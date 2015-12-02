from __future__ import division
import os
import ast
import numpy as np

from pivy import coin
import FreeCAD as App

from openglider.jsonify import load, dumps, loads
from openglider.mesh import mesh_2d
from pivy_primitives_new_new import Line

importpath = os.path.join(os.path.dirname(__file__), '..', 'demokite.ods')


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
        obj.addProperty("App::PropertyPythonObject",
                        "glider_instance", "object",
                        "glider_instance", 2)
        obj.addProperty("App::PropertyPythonObject",
                        "glider_2d", "object",
                        "parametric glider", 2)
        with open(os.path.dirname(__file__) + "/../glider2d.json", "r") as importfile:
            obj.glider_2d = load(importfile)["data"]
        obj.glider_instance = obj.glider_2d.get_glider_3d()
        obj.Proxy = self
        self.obj = obj
        super(OGGlider, self).__init__(obj)

    def __getstate__(self):
        out = {
            "glider_2d": dumps(self.obj.glider_2d),
            "name": self.obj.Name}
        return out

    def __setstate__(self, state):
        self.obj = App.ActiveDocument.getObject(state["name"])
        self.obj.addProperty("App::PropertyPythonObject",
                        "glider_instance", "object",
                        "glider_instance", 2)
        self.obj.addProperty("App::PropertyPythonObject",
                        "glider_2d", "object",
                        "parametric glider", 2)
        self.obj.glider_2d = loads(state["glider_2d"])["data"]
        self.obj.glider_instance = self.obj.glider_2d.get_glider_3d()
        return None

class OGGliderVP(OGBaseVP):
    def __init__(self, view_obj):
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
                              "outside", "visual",
                              "outside")
        view_obj.num_ribs = 0
        view_obj.profile_num = 13
        view_obj.line_num = 5
        view_obj.outside = True
        super(OGGliderVP, self).__init__(view_obj)

    def attach(self, view_obj):
        self.vis_glider = coin.SoSeparator()
        self.vis_lines = coin.SoSeparator()
        self.material = coin.SoMaterial()
        self.seperator = coin.SoSeparator()
        self.view_obj = view_obj
        self.glider_instance = view_obj.Object.glider_instance
        self.material.diffuseColor = (.7, .7, .7)
        self.seperator.addChild(self.vis_glider)
        self.seperator.addChild(self.vis_lines)
        self.seperator.addChild(self.material)
        view_obj.addDisplayMode(self.seperator, 'out')

    def updateData(self, fp=None, prop=None):
        if hasattr(self, "view_obj"):
            if prop in ["num_ribs", "profile_num", "outside", None]:
                if hasattr(self.view_obj, "profile_num"):
                    numpoints = self.view_obj.profile_num
                    if numpoints < 5:
                        numpoints = 5
                    self.update_glider(midribs=self.view_obj.num_ribs,
                                       profile_numpoints=numpoints, outside=self.view_obj.outside)
            if prop in ["line_num", None]:
                if hasattr(self.view_obj, "line_num"):
                    self.update_lines(self.view_obj.line_num)

    def update_glider(self, midribs=0, profile_numpoints=20, outside=True):
        self.vis_glider.removeAllChildren()
        glider = self.glider_instance.copy_complete()
        glider.profile_numpoints = profile_numpoints
        if outside:
            if midribs == 0:
                vertexproperty = coin.SoVertexProperty()
                mesh = coin.SoQuadMesh()
                ribs = glider.ribs
                flat_coords = [i for rib in ribs for i in rib.profile_3d.data]
                vertexproperty.vertex.setValues(0, len(flat_coords), flat_coords)
                mesh.verticesPerRow = len(ribs[0].profile_3d.data)
                mesh.verticesPerColumn = len(ribs)
                mesh.vertexProperty = vertexproperty
                self.vis_glider.addChild(mesh)
                self.vis_glider.addChild(vertexproperty)
            else:
                for cell in glider.cells:
                    sep = coin.SoSeparator()
                    vertexproperty = coin.SoVertexProperty()
                    mesh = coin.SoQuadMesh()
                    ribs = [cell.midrib(pos / (midribs + 1))
                            for pos in range(midribs + 2)]
                    flat_coords = [i for rib in ribs for i in rib]
                    vertexproperty.vertex.setValues(0,
                                                    len(flat_coords),
                                                    flat_coords)
                    mesh.verticesPerRow = len(ribs[0])
                    mesh.verticesPerColumn = len(ribs)
                    mesh.vertexProperty = vertexproperty
                    sep.addChild(vertexproperty)
                    sep.addChild(mesh)
                    self.vis_glider.addChild(sep)
        else:  # show ribs
            for rib in glider.ribs:                
                mesh = mesh_2d.from_rib(rib)
                if mesh.vertices is not None:
                    verts = list(mesh.vertices)
                    polygons = []
                    for i in mesh.polygons:
                        polygons += i
                        polygons.append(-1)


                    rib_sep = coin.SoSeparator()
                    self.vis_glider.addChild(rib_sep)
                    vertex_property = coin.SoVertexProperty()
                    face_set = coin.SoIndexedFaceSet()

                    shape_hint = coin.SoShapeHints()
                    shape_hint.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE

                    material = coin.SoMaterial()
                    material.diffuseColor = (.0, .0, .7)
                    rib_sep.addChild(material)

                    vertex_property.vertex.setValues(0, len(verts), verts)
                    face_set.coordIndex.setValues(0, len(polygons), list(polygons))
                    rib_sep.addChild(shape_hint)
                    rib_sep.addChild(vertex_property)
                    rib_sep.addChild(face_set)

            mesh = mesh_2d()
            for cell in glider.cells:
                for diagonal in cell.diagonals:
                    mesh += mesh_2d.from_diagonal(diagonal, cell)
                if mesh.vertices is not None:
                    verts = list(mesh.vertices)
                    polygons = []
                    for i in mesh.polygons:
                        polygons += i
                        polygons.append(-1)

                    diagonal_sep = coin.SoSeparator()
                    self.vis_glider.addChild(diagonal_sep)
                    vertex_property = coin.SoVertexProperty()
                    face_set = coin.SoIndexedFaceSet()

                    shape_hint = coin.SoShapeHints()
                    shape_hint.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE

                    material = coin.SoMaterial()
                    material.diffuseColor = (.7, .0, .0)
                    diagonal_sep.addChild(material)

                    vertex_property.vertex.setValues(0, len(verts), verts)
                    face_set.coordIndex.setValues(0, len(polygons), list(polygons))
                    diagonal_sep.addChild(shape_hint)
                    diagonal_sep.addChild(vertex_property)
                    diagonal_sep.addChild(face_set)




    def update_lines(self, num=3):
        self.vis_lines.removeAllChildren()
        for line in self.glider_instance.lineset.lines:
            points = line.get_line_points(numpoints=num)
            self.vis_lines.addChild(
                Line([[i[0], -i[1], i[2]] for i in points], dynamic=False))
            self.vis_lines.addChild(Line(points, dynamic=False))

    def onChanged(self, vp, prop):
        print("onChanged")
        self.updateData(vp, prop)

    def getIcon(self):
        return "new_glider.svg"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        self.updateData()
        return None
