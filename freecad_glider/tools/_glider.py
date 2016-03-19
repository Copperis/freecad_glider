from __future__ import division
import os
import numpy as np

from pivy import coin
import FreeCAD as App

from openglider.jsonify import load, dumps, loads
from openglider import mesh
from openglider.utils.distribution import Distribution
from .pivy_primitives_new_new import Line

importpath = os.path.join(os.path.dirname(__file__), '..', 'demokite.ods')


def mesh_sep(polygons, vertices, color, draw_lines=True):
    _vertices = list(vertices)
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
    shape_hint.creaseAngle = np.pi
    face_mat = coin.SoMaterial()
    face_mat.diffuseColor = color
    vertex_property.vertex.setValues(0, len(_vertices), _vertices)
    face_set.coordIndex.setValues(0, len(_polygons), list(_polygons))
    vertex_property.materialBinding = coin.SoMaterialBinding.PER_VERTEX_INDEXED
    sep += shape_hint, vertex_property, face_mat, face_set

    if draw_lines:
        line_set = coin.SoIndexedLineSet()
        line_set.coordIndex.setValues(0, len(_lines), list(_lines))
        line_mat = coin.SoMaterial()
        line_mat.diffuseColor = (.0, .0, .0)
        sep += line_mat, line_set
    return sep


class OGBaseObject(object):
    def __init__(self, obj):
        obj.Proxy = self

    def execute(self, fp):
        pass


class OGBaseVP(object):
    def __init__(self, obj):
        obj.Proxy = self

    def attach(self, vobj):
        pass

    def updateData(self, fp, prop):
        pass

    def getDisplayModes(self, obj):
        mod = ["out"]
        return(mod)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class OGGlider(OGBaseObject):
    def __init__(self, obj):
        self.obj = obj
        obj.addProperty("App::PropertyPythonObject",
                        "GliderInstance", "object",
                        "GliderInstance", 2)
        obj.addProperty("App::PropertyPythonObject",
                        "ParametricGlider", "object",
                        "ParametricGlider", 2)
        with open(os.path.dirname(__file__) + "/../glider2d.json", "r") as importfile:
            obj.ParametricGlider = load(importfile)["data"]
        obj.GliderInstance = obj.ParametricGlider.get_glider_3d()
        obj.Proxy = self
        super(OGGlider, self).__init__(obj)

    def __getstate__(self):
        out = {
            "ParametricGlider": dumps(self.obj.ParametricGlider),
            "name": self.obj.Name}
        return out

    def __setstate__(self, state):
        self.obj = App.ActiveDocument.getObject(state["name"])
        self.obj.addProperty("App::PropertyPythonObject",
                        "GliderInstance", "object",
                        "GliderInstance", 2)
        self.obj.addProperty("App::PropertyPythonObject",
                        "ParametricGlider", "object",
                        "parametric glider", 2)
        self.obj.ParametricGlider = loads(state["ParametricGlider"])["data"]
        self.obj.GliderInstance = self.obj.ParametricGlider.get_glider_3d()
        return None

class OGGliderVP(OGBaseVP):
    def __init__(self, view_obj):
        view_obj.addProperty("App::PropertyBool",
                             "ribs", "visuals",
                             "show ribs")
        view_obj.addProperty("App::PropertyInteger",
                             "num_ribs", "accuracy",
                             "num_ribs")
        view_obj.addProperty("App::PropertyInteger",
                             "profile_num", "accuracy",
                             "profile_num")
        view_obj.addProperty("App::PropertyInteger",
                             "line_num", "accuracy",
                             "line_num")
        view_obj.addProperty("App::PropertyBool",
                             "hull", "visuals",
                             "hull = True")
        view_obj.addProperty("App::PropertyBool",
                             "panels", "visuals",
                             "show panels")
        view_obj.addProperty("App::PropertyBool",
                             "half_glider", "visuals",
                             "show only one half")
        view_obj.addProperty("App::PropertyBool",
                             "draw_mesh", "visuals",
                             "draw lines of the mesh")
        view_obj.addProperty("App::PropertyInteger",
                             "hole_num", "visuals",
                             "number of hole vertices")
        view_obj.num_ribs = 0
        view_obj.profile_num = 20
        view_obj.line_num = 5
        view_obj.hull = True
        view_obj.ribs = True
        view_obj.half_glider = True
        view_obj.panels =False
        view_obj.draw_mesh = False
        view_obj.hole_num = 10
        super(OGGliderVP, self).__init__(view_obj)

    def attach(self, view_obj):
        self.vis_glider = coin.SoSeparator()
        self.vis_lines = coin.SoSeparator()
        self.material = coin.SoMaterial()
        self.seperator = coin.SoSeparator()
        self.view_obj = view_obj
        self.GliderInstance = view_obj.Object.GliderInstance
        self.material.diffuseColor = (.7, .7, .7)
        self.seperator += (self.vis_glider, self.vis_glider, self.vis_lines)
        view_obj.addDisplayMode(self.seperator, 'out')

    def updateData(self, prop="all", *args):
        self._updateData(self.view_obj, prop)

    def _updateData(self, fp, prop="all"):
        if hasattr(fp, "ribs"):      # check for last attribute to be restored
            if prop in ["num_ribs", "profile_num", "hull", "panels",
                        "half_glider", "ribs", "draw_mesh", "hole_num",
                        "all"]:
                numpoints = fp.profile_num
                numpoints = max(numpoints, 5)
                glider_changed = "half_glider" in prop or "profile_num" in prop
                self.update_glider(midribs=fp.num_ribs,
                                   profile_numpoints=numpoints,
                                   hull=fp.hull,
                                   panels=fp.panels,
                                   half=fp.half_glider,
                                   ribs=fp.ribs,
                                   draw_mesh=fp.draw_mesh,
                                   hole_num=fp.hole_num,
                                   glider_changed=glider_changed)
        if hasattr(fp, "line_num"):
            if prop in ["line_num", "half_glider", "all"]:
                self.update_lines(fp.line_num,
                                  half=fp.half_glider)

    def update_glider(self, midribs=0, profile_numpoints=20,
                      hull=True, panels=False, half=False, ribs=False,
                      draw_mesh=False, hole_num=10, glider_changed=True):
        self.vis_glider.removeAllChildren()
        if glider_changed or not hasattr(self, "glider"):
            if not half:
                self.glider = self.GliderInstance.copy_complete()
            else:
                self.glider = self.GliderInstance.copy()
        draw_glider(self.glider, self.vis_glider, midribs, profile_numpoints, 
                    hull, panels, half, ribs, draw_mesh, hole_num)


    def update_lines(self, num=3, half=False):
        self.vis_lines.removeAllChildren()
        for line in self.GliderInstance.lineset.lines:
            points = line.get_line_points(numpoints=num)
            if not half:
                self.vis_lines += (Line([[i[0], -i[1], i[2]] for i in points], dynamic=False))
            self.vis_lines += (Line(points, dynamic=False))

    def onChanged(self, vp, prop):
        self._updateData(vp, prop)

    def getIcon(self):
        return "new_glider.svg"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        # self.updateData()
        return None


def hex_to_rgb(hex_string):
    try:
        value = hex_string.split('#')[1]
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) / 256. for i in range(0, lv, lv // 3))
    except IndexError:
        return (.7, .7, .7)


def draw_glider(glider, vis_glider, midribs=0, profile_numpoints=20,
                hull=True, panels=False, half=False, ribs=False,
                draw_mesh=False, hole_num=10):
    """draw the glider to the visglider seperator"""
    glider.profile_numpoints = profile_numpoints
    count = 0
    if hull:
        if panels:
            for cell in glider.cells:
                count += 1
                for panel in cell.panels:
                    m = panel.get_mesh(cell, midribs)
                    color = (.3, .3, .3)
                    if panel.material_code:
                        color = hex_to_rgb(panel.material_code)
                    vis_glider += mesh_sep(m.polygons, m.vertices,  color, draw_mesh)

        elif midribs == 0:
            vertexproperty = coin.SoVertexProperty()
            msh = coin.SoQuadMesh()
            _ribs = glider.ribs
            flat_coords = [i for rib in _ribs for i in rib.profile_3d.data]
            vertexproperty.vertex.setValues(0, len(flat_coords), flat_coords)
            msh.verticesPerRow = len(_ribs[0].profile_3d.data)
            msh.verticesPerColumn = len(_ribs)
            msh.vertexProperty = vertexproperty
            vis_glider += msh, vertexproperty
        else:
            for cell in glider.cells:
                sep = coin.SoSeparator()
                vertexproperty = coin.SoVertexProperty()
                msh = coin.SoQuadMesh()
                _ribs = [cell.midrib(pos / (midribs + 1))
                        for pos in range(midribs + 2)]
                flat_coords = [i for rib in _ribs for i in rib]
                vertexproperty.vertex.setValues(0,
                                                len(flat_coords),
                                                flat_coords)
                msh.verticesPerRow = len(_ribs[0])
                msh.verticesPerColumn = len(_ribs)
                msh.vertexProperty = vertexproperty
                sep += vertexproperty, msh
                vis_glider += sep
    if ribs:  # show ribs
        msh = mesh.Mesh()
        for rib in glider.ribs:
            if not rib.profile_2d.has_zero_thickness:
                msh += mesh.Mesh.from_rib(rib, hole_num, mesh_option="QYqazip")
        if msh.vertices is not None:
            vis_glider += mesh_sep(msh.polygons, msh.vertices, (.3, .3, .3), draw_mesh)
            # verts = list(msh.vertices)
            # polygons = []
            # lines = []
            # for i in msh.polygons:
            #     polygons += i
            #     lines += i
            #     lines.append(i[0])
            #     polygons.append(-1)
            #     lines.append(-1)

            # rib_sep = coin.SoSeparator()
            # vis_glider += rib_sep
            # vertex_property = coin.SoVertexProperty()
            # face_set = coin.SoIndexedFaceSet()
            # line_set = coin.SoIndexedLineSet()

            # shape_hint = coin.SoShapeHints()
            # shape_hint.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE

            # mat1 = coin.SoMaterial()
            # mat1.diffuseColor = (.3, .3, .3)
            # mat2 = coin.SoMaterial()
            # mat2.diffuseColor = (.0, .0, .0)

            # vertex_property.vertex.setValues(0, len(verts), verts)
            # face_set.coordIndex.setValues(0, len(polygons), list(polygons))
            # line_set.coordIndex.setValues(0, len(lines), list(lines))
            # rib_sep += shape_hint, vertex_property, mat1, face_set
            # if draw_mesh:
            #     rib_sep += mat2, line_set


        msh = mesh.Mesh()
        for cell in glider.cells:
            for diagonal in cell.diagonals:
                msh += mesh.Mesh.from_diagonal(diagonal, cell, insert_points=4)
            if msh.vertices is not None:
                vis_glider += mesh_sep(msh.polygons, msh.vertices, (.3, .3, .3), draw_mesh)

        _strap_verts = []
        _strap_lines = []
        _strap_count = 0
        for cell in glider.cells:
            for i, strap in enumerate(cell.straps):
                _strap_verts += strap.get_3d(cell)
                _strap_lines += [_strap_count * 2, _strap_count * 2 + 1, -1]
                _strap_count += 1
        strap_sep = coin.SoSeparator()
        vis_glider += strap_sep
        strap_material = coin.SoMaterial()
        strap_material.diffuseColor = (0., 0., 0.)
        strap_verts = coin.SoVertexProperty()
        strap_set = coin.SoIndexedLineSet()
        strap_verts.vertex.setValues(0, len(_strap_verts), _strap_verts)
        strap_set.coordIndex.setValues(0, len(_strap_lines), _strap_lines)

        strap_sep += strap_material, strap_verts, strap_set
