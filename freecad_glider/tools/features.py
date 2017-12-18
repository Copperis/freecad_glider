from ._glider import OGBaseObject, OGGliderVP

from openglider.airfoil.profile_2d import Profile2D
from openglider.glider.rib import SingleSkinRib
import numpy as np
import copy

class BaseFeature(OGBaseObject):
    def __init__(self, obj, parent):
        self.obj = obj
        obj.addProperty('App::PropertyLink', 'parent', 'not yet', 'docs')
        obj.parent = parent
        super(BaseFeature, self).__init__(obj)

    def drawGlider(self, call_parent=True):
        if not self.obj.ViewObject.Visibility:
            self.obj.ViewObject.Proxy.recompute = True
            if call_parent:
                self.obj.parent.Proxy.drawGlider()
        else:
            self.obj.ViewObject.Proxy.recompute = True
            self.obj.ViewObject.Proxy.updateData()
            if call_parent:
                self.obj.parent.Proxy.drawGlider()

    def getGliderInstance(self):
        '''adds stuff and returns changed copy'''
        return copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())

    def getParametricGlider(self):
        '''returns top level parametric glider'''
        return self.obj.parent.Proxy.getParametricGlider()

    def setParametricGlider(self, obj):
        '''sets the top-level glider2d and recomputes the glider3d'''
        self.obj.parent.Proxy.setParametricGlider(obj)

    def getRoot(self):
        '''return the root freecad obj'''
        return self.obj.parent.Proxy.getRoot()

    def onDocumentRestored(self, obj):
        self.obj = obj
        self.obj.parent.Proxy.onDocumentRestored(self.obj.parent)
        self.obj.ViewObject.Proxy.addProperties(self.obj.ViewObject)
        if not self.obj.ViewObject.Visibility:
            self.obj.ViewObject.Proxy.recompute = True
        else:
            self.obj.ViewObject.Proxy.recompute = True
            self.obj.ViewObject.Proxy.updateData(prop='Visibility')

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def execute(self, fp):
        self.drawGlider()

class RibFeature(BaseFeature):
    def __init__(self, obj, parent):
        super(RibFeature, self).__init__(obj, parent)
        obj.addProperty('App::PropertyIntegerList', 'ribs', 'not yet', 'docs')
        obj.addProperty('App::PropertyInteger', 'airfoil', 'not yet', 'docs')

    def getGliderInstance(self):
        glider = copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())
        airfoil = self.obj.parent.Proxy.getParametricGlider().profiles[self.obj.airfoil]
        for i, rib in enumerate(glider.ribs):
            if i in self.obj.ribs:
                rib.profile_2d = airfoil
        return glider


class BallooningFeature(BaseFeature):
    def __init__(self, obj, parent):
        super(BallooningFeature, self).__init__(obj, parent)
        obj.addProperty('App::PropertyIntegerList', 'cells', 'not yet', 'docs')
        obj.addProperty('App::PropertyInteger', 'ballooning', 'not yet', 'docs')

    def getGliderInstance(self):
        glider = copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())
        ballooning = self.obj.parent.Proxy.getParametricGlider().balloonings[self.obj.ballooning]
        for i, cell in enumerate(glider.cells):
            if i in self.obj.cells:
                cell.ballooning = ballooning
        return glider


class SharkFeature(BaseFeature):
    def __init__(self, obj, parent):
        super(SharkFeature, self).__init__(obj, parent)
        self.addProperty('ribs', [], 'not_yet', 'docs', int)
        self.addProperty('x1', 0.1, 'not_yet', 'distance')
        self.addProperty('x2', 0.11, 'not_yet', 'distance')
        self.addProperty('x3', 0.5, 'not_yet', 'distance')
        self.addProperty('y_add', 0.1, 'not_yet', 'amount')
        self.addProperty('type', False, 'not_yet', '0-> linear, 1->quadratic')

    def apply(self, airfoil_data, x1, x2, x3, y_add):
        data = []
        for x, y in copy.copy(airfoil_data):
            if y < 0:
                if x > x1 and x < x2:
                    y -= y_add * (x - x1) / (x2 - x1)  # here any function
                elif x > x2 and x < x3:
                    y -= y_add * (x3 - x) / (x3 - x2)  # here another function
            data.append([x, y])
        return np.array(data)

    def getGliderInstance(self):
        x1, x2, x3, y_add =  self.obj.x1, self.obj.x2, self.obj.x3, self.obj.y_add
        from openglider.airfoil.profile_2d import Profile2D
        glider = copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())
        for rib in enumerate(glider.ribs):
            rib.profile_2d = Profile2D(self.apply(rib.profile_2d._data, x1, x2, x3, y_add))
        return glider


class SingleSkinRibFeature(BaseFeature):
    def __init__(self, obj, parent):
        super(SingleSkinRibFeature, self).__init__(obj, parent)
        obj.addProperty('App::PropertyIntegerList',
                        'ribs', 'not yet', 'docs')
        self.addProperties()

    def getGliderInstance(self):
        glider = copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())
        new_ribs = []
        self.addProperties()

        single_skin_par = {'att_dist': self.obj.att_dist,
                           'height': self.obj.height,
                           'num_points': self.obj.num_points,
                           'le_gap': self.obj.le_gap,
                           'te_gap': self.obj.te_gap,
                           'double_first': self.obj.double_first}

        for i, rib in enumerate(glider.ribs):
            if i in self.obj.ribs:
                if not isinstance(rib, SingleSkinRib):
                    new_ribs.append(SingleSkinRib.from_rib(rib, single_skin_par))
                else:
                    rib.single_skin_par = single_skin_par
                    new_ribs.append(rib)
            else:
                new_ribs.append(rib)
        glider.replace_ribs(new_ribs)
        return glider

    def addProperties(self):
        self.addProperty('height', 0.5, 'not yet', 'docs')
        self.addProperty('att_dist', 0.1, 'not yet', 'docs')
        self.addProperty('num_points', 20, 'accuracy', 'number of points')
        self.addProperty('le_gap', 'not_yet', True, 'should the leading edge match the rib')
        self.addProperty('te_gap', 'not_yet', True, 'should the leading edge match the rib')
        self.addProperty('double_first', False, 'not yet', 'this is for double a lines')


class FlapFeature(BaseFeature):
    def __init__(self, obj, parent):
        super(FlapFeature, self).__init__(obj, parent)
        self.addProperties()

    def addProperties(self):
        self.addProperty('flap_begin', 0.95, 'flap', 'where should the flapping effect start', float)
        self.addProperty('flap_amount', 0.01, 'flap', 'how much flapping', float)
        self.addProperty('flap_ribs', [], 'flap', 'which ribs get flapped', int)

    def getGliderInstance(self):
        glider = copy.deepcopy(self.obj.parent.Proxy.getGliderInstance())
        new_ribs = []
        self.addProperties()

        for i, rib in enumerate(glider.ribs):
            if i in self.obj.flap_ribs:
                rib.profile_2d.set_flap(self.obj.flap_begin, self.obj.flap_amount)
        return glider