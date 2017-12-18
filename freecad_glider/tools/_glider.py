from __future__ import division
import os
import numpy as np

import FreeCAD as App

from openglider import jsonify
from openglider import mesh
from openglider.glider.cell.elements import TensionLine
from . import pivy_primitives_new_new as prim
from ._tools import coin, hex_to_rgb


def coin_SoSwitch(parent, name):
    switch = coin.SoSwitch()
    switch.setName(name)
    parent += [switch]
    return switch

importpath = os.path.join(os.path.dirname(__file__), '..', 'demokite.ods')


# a list of all deafault parameters
preference_table = {'default_show_half_glider': (bool, True),
                    'default_show_panels': (bool, False),
                    'default_num_prof_points': (int, 20),
                    'default_num_cell_points': (int, 0),
                    'default_num_line_points': (int, 2),
                    'default_num_hole_points': (int, 10)}


def get_parameter(name):
    glider_defaults = App.ParamGet('User parameter:BaseApp/Preferences/Mod/glider')
    if preference_table[name][0] == bool:
        return glider_defaults.GetBool(name, preference_table[name][1])
    elif preference_table[name][0] == int:
        return glider_defaults.GetInt(name, preference_table[name][1])


def refresh():
    print('reloading')
    reload(coin)
    reload(jsonify)
    reload(mesh)
    reload(prim)


def mesh_sep(mesh, color, draw_lines=False):
    vertices, polygons_grouped, _ = mesh.get_indexed()
    polygons = sum(polygons_grouped.values(), [])
    _vertices = [list(v) for v in vertices]
    _polygons = []
    _lines = []
    for i in polygons:
        _polygons += i
        _lines += i
        _lines.append(i[0])
        _polygons.append(-1)
        _lines.append(-1)

    sep = coin.SoSeparator()
    vertex_property = coin.SoVertexProperty()
    face_set = coin.SoIndexedFaceSet()
    shape_hint = coin.SoShapeHints()
    shape_hint.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    shape_hint.creaseAngle = np.pi / 3
    face_mat = coin.SoMaterial()
    face_mat.diffuseColor = color
    vertex_property.vertex.setValues(0, len(_vertices), _vertices)
    face_set.coordIndex.setValues(0, len(_polygons), list(_polygons))
    vertex_property.materialBinding = coin.SoMaterialBinding.PER_VERTEX_INDEXED
    sep += [shape_hint, vertex_property, face_mat, face_set]

    if draw_lines:
        line_set = coin.SoIndexedLineSet()
        line_set.coordIndex.setValues(0, len(_lines), list(_lines))
        line_mat = coin.SoMaterial()
        line_mat.diffuseColor = (.0, .0, .0)
        sep += [line_mat, line_set]
    return sep

def _addProperty(obj, name, value, group, docs, p_type=None):
    '''
    property_list:
    property_name property_value, property_group, property_docs
    '''
    if hasattr(obj, name):
        return
    type_dict = {
        bool: 'App::PropertyBool',
        int: 'App::PropertyInteger',
        float: 'App::PropertyFloat',
        str: 'App::PropertyString',
        'link': 'App::PropertyLink'
    }
    list_types = {
        bool: 'App::PropertyBoolList',
        int: 'App::PropertyIntegerList',
        float: 'App::PropertyFloatList',
        str: 'App::PropertyStringList',
        'link': 'App::PropertyLinkList'
    }
    p_type = p_type or type(value)
    is_list = (type(value) == list)
    if p_type == list:
        is_list = True
        p_type = type(value[0])
        for i in value:
            if type(i) != p_type:
                raise(AttributeError('list must not have different elements'))
    if is_list:
        fc_type = list_types[p_type]
    else:
        fc_type = type_dict[p_type]
    obj.addProperty(fc_type, name, group, docs)
    setattr(obj, name, value)


class OGBaseObject(object):
    def __init__(self, obj):
        obj.Proxy = self
        self.obj = obj

    def execute(self, fp):
        pass

    def addProperty(self, name, value, group, docs, p_type=None):
        _addProperty(self.obj, name, value, group, docs, p_type)


class OGBaseVP(object):
    def __init__(self, view_obj):
        view_obj.Proxy = self
        self.view_obj = view_obj
        self.obj = view_obj.Object

    def addProperty(self, name, value, group, docs, p_type=None):
        _addProperty(self.obj, name, value, group, docs, p_type)        

    def attach(self, view_obj):
        self.view_obj = view_obj
        self.obj = view_obj.Object

    def updateData(self, fp, prop):
        pass

    def getDisplayModes(self, obj):
        mod = ['out']
        return(mod)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class OGGlider(OGBaseObject):
    def __init__(self, obj, parametric_glider=None, import_path=None):
        obj.addProperty('App::PropertyPythonObject',
                        'GliderInstance', 'object',
                        'GliderInstance', 2)
        obj.addProperty('App::PropertyPythonObject',
                        'ParametricGlider', 'object',
                        'ParametricGlider', 2)
        if parametric_glider:
            obj.ParametricGlider = parametric_glider
        else:
            import_path = import_path or os.path.dirname(__file__) + '/../glider2d.json'
            with open(import_path, 'r') as importfile:
                obj.ParametricGlider = jsonify.load(importfile)['data']
        obj.GliderInstance = obj.ParametricGlider.get_glider_3d()
        super(OGGlider, self).__init__(obj)

    def drawGlider(self):
        if not self.obj.ViewObject.Visibility:
            self.obj.ViewObject.Proxy.recompute = True
        else:
            self.obj.ViewObject.Proxy.recompute = False
            self.obj.ViewObject.Proxy.updateData()

    def getGliderInstance(self):
        return self.obj.GliderInstance

    def getParametricGlider(self):
        '''returns top level parametric glider'''
        return self.obj.ParametricGlider

    def setParametricGlider(self, parametric_glider):
        '''sets the top-level glider2d and recomputes the glider3d'''
        self.obj.ParametricGlider = parametric_glider
        self.obj.GliderInstance = parametric_glider.get_glider_3d()
        App.ActiveDocument.recompute()

    def getRoot(self):
        '''return the root freecad obj'''
        return self.obj

    def __getstate__(self):
        out = {
            'ParametricGlider': jsonify.dumps(self.obj.ParametricGlider),
            'name': self.obj.Name}
        return out

    def __setstate__(self, state):
        obj = App.ActiveDocument.getObject(state['name'])
        obj.ParametricGlider = jsonify.loads(state['ParametricGlider'])['data']
        obj.GliderInstance = obj.ParametricGlider.get_glider_3d()
        return None

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.obj.ViewObject.Proxy.addProperties(self.obj.ViewObject)
        if not self.obj.ViewObject.Visibility:
            self.obj.ViewObject.Proxy.recompute = True
        else:
            self.obj.ViewObject.Proxy.recompute = True
            self.obj.ViewObject.Proxy.updateData(prop='Visibility')


class OGGliderVP(OGBaseVP):
    def __init__(self, view_obj):
        view_obj.addProperty('App::PropertyBool',
                             'ribs', 'visuals',
                             'show ribs')
        view_obj.addProperty('App::PropertyInteger',
                             'num_ribs', 'accuracy',
                             'num_ribs')
        view_obj.addProperty('App::PropertyInteger',
                             'profile_num', 'accuracy',
                             'profile_num')
        view_obj.addProperty('App::PropertyInteger',
                             'hole_num', 'accuracy',
                             'number of hole vertices')
        view_obj.addProperty('App::PropertyInteger',
                             'line_num', 'accuracy',
                             'line_num')
        view_obj.addProperty('App::PropertyEnumeration',
                             'hull', 'visuals')
        view_obj.addProperty('App::PropertyBool',
                             'half_glider', 'visuals',
                             'show only one half')
        view_obj.num_ribs = get_parameter('default_num_cell_points')
        view_obj.profile_num = get_parameter('default_num_prof_points')
        view_obj.line_num = get_parameter('default_num_line_points')
        view_obj.hull = ['panels', 'smooth', 'simple', 'None']
        view_obj.ribs = True
        view_obj.half_glider = get_parameter('default_show_half_glider')
        view_obj.hole_num = get_parameter('default_num_hole_points')
        self.addProperties(view_obj)
        self.recompute = False
        super(OGGliderVP, self).__init__(view_obj)

    def addProperties(self, view_object):
        self.view_obj = view_object
        if not hasattr(self.view_obj, 'fill_ribs'):
            self.view_obj.addProperty('App::PropertyBool',
                                 'fill_ribs', 'visuals', 'fill ribs')
            self.view_obj.fill_ribs = False


    def getGliderInstance(self, view_obj):
        try:
            return self.obj.Proxy.getGliderInstance()
        except AttributeError as e:
            print(e)
            return None

    def attach(self, view_obj):
        super(OGGliderVP, self).attach(view_obj)
        self.vis_glider = coin.SoSeparator()
        self.vis_lines = coin.SoSeparator()
        self.material = coin.SoMaterial()
        self.seperator = coin.SoSeparator()
        self.vis_glider.setName('vis_glider')
        self.vis_lines.setName('vis_lines')
        self.material.setName('material')
        self.seperator.setName('baseseperator')
        self.material.diffuseColor = (.7, .7, .7)
        self.seperator += [self.vis_glider, self.vis_lines]
        pick_style = coin.SoPickStyle()
        pick_style.style.setValue(coin.SoPickStyle.BOUNDING_BOX)
        self.vis_glider += [pick_style]
        self.vis_lines += [pick_style]
        view_obj.addDisplayMode(self.seperator, 'out')

    def updateData(self, prop='all', *args):
        self._updateData(self.view_obj, prop)

    def _updateData(self, fp, prop='all'):
        if not self.getGliderInstance(fp):
            return
        if not hasattr(fp, 'Visibility') or not fp.Visibility:
            return
        if prop in ['Visibility'] and fp.Proxy.recompute:
            prop = 'all'
        if not hasattr(fp, 'half_glider'):
            return  # the vieprovider isn't set up at this moment
                    # but calls already the update function
        if prop == 'profile_num' and fp.profile_num < 20:
            return # don't do anything if profile_num is smaller than 20
        if not hasattr(self, 'glider'):
            if not fp.half_glider:
                self.glider = self.getGliderInstance(fp).copy_complete()
            else:
                self.glider = self.getGliderInstance(fp).copy()
        if hasattr(fp, 'ribs'):      # check for last attribute to be restored
            if prop in ['all', 'profile_num', 'num_ribs', 'half_glider']:
                self.vis_glider.removeChild(self.vis_glider.getByName('hull'))

            if prop in ['all', 'hole_num', 'profile_num', 'half_glider', 'fill_ribs']:
                self.vis_glider.removeChild(self.vis_glider.getByName('ribs'))

            if (prop in ['num_ribs', 'profile_num', 'hull', 'panels',
                         'half_glider', 'ribs', 'hole_num', 'fill_ribs', 'all']):
                numpoints = fp.profile_num
                numpoints = max(numpoints, 5)
                glider_changed = (prop in ['half_glider', 'profile_num', 'all'])
                if glider_changed:
                    if not fp.half_glider:
                        self.glider = self.getGliderInstance(fp).copy_complete()
                    else:
                        self.glider = self.getGliderInstance(fp).copy()

                self.update_glider(midribs=fp.num_ribs,
                                   profile_numpoints=numpoints,
                                   hull=fp.hull,
                                   ribs=fp.ribs,
                                   hole_num=fp.hole_num,
                                   glider_changed=glider_changed,
                                   fill_ribs=fp.fill_ribs)
                fp.Proxy.recompute = False
        if hasattr(fp, 'line_num'):
            if prop in ['line_num', 'half_glider', 'all']:
                self.update_lines(fp.line_num)

    def update_glider(self, midribs=0, profile_numpoints=20,
                      hull='panels', ribs=False, 
                      hole_num=10, glider_changed=True, fill_ribs=True):
        draw_glider(self.glider, vis_glider=self.vis_glider, midribs=midribs, 
                    hole_num=hole_num, profile_num=profile_numpoints,
                    hull=hull, ribs=ribs, fill_ribs=fill_ribs)

    def update_lines(self, num=3):
        self.vis_lines.removeAllChildren()
        if num < 2:
            return
        self.glider.lineset.recalc()
        for line in self.glider.lineset.lines:
            points = line.get_line_points(numpoints=num)
            self.vis_lines += [prim.Line(points, dynamic=False)]

    def onChanged(self, vp, prop):
        self._updateData(vp, prop)

    def getIcon(self):
        return 'new_glider.svg'

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def draw_glider(glider, vis_glider=None, midribs=0, hole_num=10, profile_num=20,
                  hull='panels', ribs=False, elements=False, fill_ribs=True):
    '''draw the glider to the visglider seperator'''
    glider.profile_numpoints = profile_num

    vis_glider = vis_glider or coin.SoSeparator()
    if vis_glider.getByName('hull') is None:        # TODO: fix bool(sep_without_children) -> False pivy
        hull_sep = coin_SoSwitch(vis_glider, 'hull')
    else:
        hull_sep = vis_glider.getByName('hull')

    draw_ribs = not vis_glider.getByName('ribs')
    draw_panels = not hull_sep.getByName('panels')
    draw_smooth = not hull_sep.getByName('smooth')
    draw_simple = not hull_sep.getByName('simple')

    def setHullType(name):
        for i in range(len(hull_sep)):
            if hull_sep[i].getName() == name:
                hull_sep.whichChild = i
                break
        else:
            hull_sep.whichChild = -1

    if hull == 'panels' and draw_panels:
        hull_panels_sep = coin.SoSeparator()
        hull_panels_sep.setName('panels')
        for cell in glider.cells:
            for panel in cell.panels:
                m = panel.get_mesh(cell, midribs, with_numpy=True)
                if panel.material_code:
                    color = hex_to_rgb(panel.material_code)
                hull_panels_sep += [mesh_sep(m,  color)]
        hull_sep += [hull_panels_sep]

    elif hull == 'smooth' and draw_smooth:
        hull_smooth_sep = coin.SoSeparator()
        hull_smooth_sep.setName('smooth')
        vertexproperty = coin.SoVertexProperty()
        msh = coin.SoQuadMesh()
        _ribs = glider.ribs
        flat_coords = [i for rib in _ribs for i in rib.profile_3d.data]
        vertexproperty.vertex.setValues(0, len(flat_coords), flat_coords)
        msh.verticesPerRow = len(_ribs[0].profile_3d.data)
        msh.verticesPerColumn = len(_ribs)
        msh.vertexProperty = vertexproperty
        hull_smooth_sep += [msh, vertexproperty]
        hull_sep += [hull_smooth_sep]

    elif hull == 'simple' and draw_simple:
        hull_simple_sep = coin.SoSeparator()
        hull_simple_sep.setName('simple')
        for cell in glider.cells:
            m = cell.get_mesh(midribs, with_numpy=True)
            color = (.8, .8, .8)
            hull_simple_sep += [mesh_sep(m,  color)]
        hull_sep += [hull_simple_sep]

    setHullType(hull)

    if ribs and draw_ribs:
        rib_sep = coin.SoSwitch()
        rib_sep.setName('ribs')
        msh = mesh.Mesh()
        line_msh = mesh.Mesh()
        for rib in glider.ribs:
            if not rib.profile_2d.has_zero_thickness:
                msh += mesh.Mesh.from_rib(rib, hole_num, mesh_option='QYqazip', glider=glider, filled=fill_ribs)
        if msh.vertices is not None:
            rib_sep += [mesh_sep(msh, (.3, .3, .3), draw_lines = not fill_ribs)]

        msh = mesh.Mesh()
        for cell in glider.cells:
            for diagonal in cell.diagonals:
                msh += mesh.Mesh.from_diagonal(diagonal, cell, insert_points=4)

            for strap in cell.straps:
                if isinstance(strap, TensionLine):
                    line_msh += strap.get_mesh(cell)
                else:
                    msh += mesh.Mesh.from_diagonal(strap, cell, insert_points=4)

        if msh.vertices is not None:
            rib_sep += [mesh_sep(msh, (.3, .3, .3))]
        if line_msh.vertices is not None:
            rib_sep += [mesh_sep(line_msh, (.3, .3, .3), draw_lines=True)]
        vis_glider += [rib_sep]

    rib_sep = vis_glider.getByName('ribs')
    if ribs:
        rib_sep.whichChild = coin.SO_SWITCH_ALL
    else:
        if hasattr(rib_sep, 'whichChild'):
            rib_sep.whichChild = coin.SO_SWITCH_NONE
