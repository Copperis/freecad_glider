# -*- coding: utf-8 -*-
from __future__ import division
import numpy
from pivy import coin
from PySide import QtGui

from ._tools import base_tool, text_field, input_field, spline_select
from .pivy_primitives import Line, ControlPointContainer, vector3D


class zrot_tool(base_tool):
    num_on_drag = 80
    num_release = 200

    def __init__(self, obj):
        super(zrot_tool, self).__init__(obj)
        pts = vector3D(
            numpy.array(self.spline.controlpoints) * self.scale)
        self.aoa_cpc = ControlPointContainer(pts, self.view)
        self.shape = coin.SoSeparator()
        self.coords = coin.SoSeparator()
        self.grid = coin.SoSeparator()
        self.aoa_spline = Line([], color="red", width=2)
        self.ribs = self.glider_2d.shape.ribs
        self.front = [rib[0] for rib in self.ribs]
        self.back = [rib[1] for rib in self.ribs]
        self.text_scale = self.glider_2d.shape.span / len(self.front) / 15
        self.x_grid = [i[0] for i in self.front]

        self.Qnum_aoa = QtGui.QSpinBox(self.base_widget)
        self.spline_select = spline_select(
            [self.spline], self.update_spline_type, self.base_widget)

        self.setup_widget()
        self.setup_pivy()

    @property
    def spline(self):
        return self.glider_2d.zrot

    @property
    def scale(self):
        return numpy.array([1., 1.])
    

    def setup_pivy(self):
        self.aoa_cpc.control_points[-1].constraint = lambda pos: [
            self.glider_2d.shape.span, pos[1], pos[2]]
        self.task_separator.addChild(self.aoa_cpc)
        self.task_separator.addChild(self.shape)
        self.task_separator.addChild(self.aoa_spline.object)
        self.task_separator.addChild(self.coords)
        self.task_separator.addChild(self.grid)
        self.update_aoa()
        self.update_grid()
        self.draw_shape()

    def setup_widget(self):
        self.layout.setWidget(0, text_field, QtGui.QLabel("num_points"))
        self.layout.setWidget(0, input_field, self.Qnum_aoa)
        self.layout.setWidget(1, text_field, QtGui.QLabel("spline type"))
        self.layout.setWidget(1, input_field, self.spline_select)

        self.Qnum_aoa.setValue(len(self.spline.controlpoints))
        self.Qnum_aoa.setMaximum(5)
        self.Qnum_aoa.setMinimum(2)
        self.Qnum_aoa.valueChanged.connect(self.update_num)
        self.aoa_cpc.on_drag.append(self.update_aoa)
        self.aoa_cpc.drag_release.append(self.update_grid)

    def draw_shape(self):
        self.shape.removeAllChildren()
        self.shape.addChild(Line(self.front, color="grey").object)
        self.shape.addChild(Line(self.back, color="grey").object)
        for rib in self.ribs:
            self.shape.addChild(Line(rib, color="grey").object)

    def update_aoa(self):
        self.spline.controlpoints = (
            numpy.array([i[:-1] for i in self.aoa_cpc.control_pos]) /
            self.scale).tolist()
        self.aoa_spline.update(
            self.spline.get_sequence(num=self.num_on_drag) * self.scale)

    def update_spline_type(self):
        self.aoa_cpc.control_pos = vector3D(
            numpy.array(self.spline.controlpoints) * self.scale)
        self.aoa_cpc.control_points[-1].constraint = lambda pos: [
            self.glider_2d.shape.span, pos[1], pos[2]]
        self.update_aoa()

    def update_grid(self):
        self.coords.removeAllChildren()
        pts = self.spline.get_sequence(num=self.num_on_drag)
        self.aoa_spline.update(pts * self.scale)
        max_x = max([i[0] for i in pts])
        max_y = max([i[1] for i in pts])
        min_y = min([i[1] for i in pts])

        self.coords.addChild(
            Line([[0, 0], [0., max_y * 1.3 * self.scale[1]]]).object)
        self.coords.addChild(
            Line([[0, 0], [max_x * 1.3, 0.]]).object)
        # transform to scale + transform to degree
        min_y *= 180 / numpy.pi
        max_y *= 180 / numpy.pi
        # if min_y > 0 miny = 0
        min_y = (min_y < 0) * (min_y - 1)
        # create range
        _range = range(int(max_y) - int(min_y) + 2)
        # transform back
        y_grid = [(i + int(min_y)) * numpy.pi * self.scale[1] / 180
                  for i in _range]
        self._update_grid(self.x_grid, y_grid)

    def accept(self):
        self.aoa_cpc.remove_callbacks()
        self.obj.glider_2d = self.glider_2d
        self.glider_2d.get_glider_3d(self.obj.glider_instance)
        super(zrot_tool, self).accept()
        self.update_view_glider()

    def reject(self):
        self.aoa_cpc.remove_callbacks()
        super(zrot_tool, self).reject()

    def grid_points(self, grid_x, grid_y):
        return [[x, y] for y in grid_y for x in grid_x]

    def _update_grid(self, grid_x, grid_y):
        self.grid.removeAllChildren()
        x_points_lower = [[x, grid_y[0], -0.001] for x in grid_x]
        x_points_upper = [[x, grid_y[-1], -0.001] for x in grid_x]
        y_points_lower = [[grid_x[0], y, -0.001] for y in grid_y]
        y_points_upper = [[grid_x[-1], y, -0.001] for y in grid_y]
        for l in zip(x_points_lower, x_points_upper):
            self.grid.addChild(Line(l, color="grey").object)
        for l in zip(y_points_lower, y_points_upper):
            self.grid.addChild(Line(l, color="grey").object)
        for l in y_points_upper:
            textsep = coin.SoSeparator()
            text = coin.SoText2()
            trans = coin.SoTranslation()
            trans.translation = l
            text.string = str(l[1] * 180 / numpy.pi / self.scale[1]) + "°"
            textsep.addChild(trans)
            self.grid.addChild(textsep)
            textsep.addChild(text)
        aoa_int = self.spline.interpolation(50)
        for i in self.back:
            textsep = coin.SoSeparator()
            scale = coin.SoScale()
            text = coin.SoAsciiText()
            trans = coin.SoTranslation()
            rot = coin.SoRotationXYZ()
            rot.axis = coin.SoRotationXYZ.Z
            rot.angle.setValue(numpy.pi / 2)
            scale.scaleFactor = (
                self.text_scale, self.text_scale, self.text_scale)
            trans.translation = (i[0], i[1], 0.001)
            text.string = str(aoa_int(i[0]) * 180 / numpy.pi)[:6]
            textsep.addChild(trans)
            textsep.addChild(scale)
            textsep.addChild(rot)
            self.grid.addChild(textsep)
            textsep.addChild(text)

    def update_num(self):
        self.spline.numpoints = self.Qnum_aoa.value()
        self.aoa_cpc.control_pos = vector3D(
            numpy.array(self.spline.controlpoints) * self.scale)
        self.aoa_cpc.control_points[-1].constraint = lambda pos: [
            self.glider_2d.shape.span, pos[1], pos[2]]
        self.update_aoa()


class aoa_tool(zrot_tool):
    @property
    def spline(self):
        return self.glider_2d.aoa

    @property
    def scale(self):
        return numpy.array([1., 8.])

    def setup_widget(self):
        super(aoa_tool, self).setup_widget()
        self.QGlide = QtGui.QDoubleSpinBox(self.base_widget)
        self.QGlide.setValue(self.glider_2d.glide)
        self.layout.setWidget(3, text_field, QtGui.QLabel("glidenumber"))
        self.layout.setWidget(3, input_field, self.QGlide)

    def accept(self):
        self.glider_2d.glide = self.QGlide.value()
        super(aoa_tool, self).accept()