import math
import os
import re
import json
from pprint import pprint
from collections import OrderedDict
from operator import add

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as OpenMaya


def get_matrix_from_ue4(transform):
    '''
    based on code supplied by Rogers
    '''
    print transform
    rotate_order = [0,1,2]
    translateX,translateY,translateZ = [float(i) for i in transform[0]]
    roll, pitch, yaw = [[float(i) for i in transform[1]][j] for j in rotate_order]
    scaleX,scaleY,scaleZ = [float(i) for i in transform[2]]
    SP,SY,SR = [math.sin(math.radians(angle)) for angle in [pitch, yaw, roll]]
    CP,CY,CR = [math.cos(math.radians(angle)) for angle in [pitch, yaw, roll]]
    matrix_list = []

    matrix_list.append((CP * CY) * scaleX)
    matrix_list.append((CP * SY) * scaleX)
    matrix_list.append(SP * scaleX)
    matrix_list.append(0.0)

    matrix_list.append((SR * SP * CY - CR * SY) * scaleY)
    matrix_list.append((SR * SP * SY + CR * CY) * scaleY)
    matrix_list.append((- SR * CP) * scaleY)
    matrix_list.append(0.0)

    matrix_list.append(( -( CR * SP * CY + SR * SY ) ) * scaleZ)
    matrix_list.append((CY * SR - CR * SP * SY) * scaleZ)
    matrix_list.append((CR * CP) * scaleZ)
    matrix_list.append(0.0)

    matrix_list.append(translateX)
    matrix_list.append(translateY)
    matrix_list.append(translateZ)
    matrix_list.append(1.0)

    return matrix_list


def get_matrix(node):
    selection = OpenMaya.MSelectionList()
    matrix_obj = OpenMaya.MObject()
    selection.add(node)
    # New api is nice since it will just return an MObject instead of taking two arguments.
    MObjectA = selection.getDependNode(0)
    # Dependency node so we can get the worldMatrix attribute
    fnThisNode = OpenMaya.MFnDependencyNode(MObjectA)
    # Get it's world matrix plug
    world_matrix_attr = fnThisNode.attribute("worldMatrix")
    # Getting mPlug by plugging in our MObject and attribute
    matrix_plug = OpenMaya.MPlug(MObjectA, world_matrix_attr)
    matrix_plug = matrix_plug.elementByLogicalIndex(0)
    # Get matrix plug as MObject so we can get it's data.
    matrix_obj = matrix_plug.asMObject()
    #Finally get the data
    world_matrix_data = OpenMaya.MFnMatrixData(matrix_obj)
    world_matrix = world_matrix_data.matrix()
    return world_matrix


def decompose_matrix(node,matrix):
    '''
    Decomposes a MMatrix in new api.
    Returns list of translation, rotation, scale in world space.
    '''
    #Rotate order of object
    rotation_order = cmds.getAttr('%s.rotateOrder' % node)
    #Puts matrix into transformation matrix
    m_transform_matrix = OpenMaya.MTransformationMatrix(matrix)
    #Translation Values
    translate = m_transform_matrix.translation(OpenMaya.MSpace.kWorld)
    #Euler rotation value in radians
    euler_rotation = m_transform_matrix.rotation()
    #Reorder rotation order based on ctrl.
    euler_rotation.reorderIt(rotation_order)
    #Find degrees
    angles = [math.degrees(angle) for angle in (euler_rotation.x, euler_rotation.y, euler_rotation.z)]
    #Find world scale of our object.
    scale = m_transform_matrix.scale(OpenMaya.MSpace.kWorld)
    #Return Values
    return [translate.x,translate.y,translate.z], angles, scale


def matrix_to_list(mtx):
    lst=[]
    for row in range(0,4):
        for col in range(0,4):
            lst.append(mtx.getElement(row,col))
    return lst


def list_to_matrix(lst):
    mtx=OpenMaya.MMatrix(lst)
    # OpenMaya.MScriptUtil.createMatrixFromList(lst, mtx)
    return mtx


def get_matrix_for_node(node, frame_start=1, frame_end=100, frame_step=1):
    mtx=[]
    for frame in range(int(frame_start),int(frame_end),int(frame_step)):
        mtx.append(cmds.getAttr("%s.wm" % node, t=frame))
    return mtx


def apply_matrix_obj(mtx, node):
    mtx = matrix_to_list(mtx)
    cmds.xform(node, ws=True, m=mtx)
    cmds.setKeyframe(node)


def apply_matrix_list(mtx, node):
    cmds.xform(node, ws=True, m=mtx)
    cmds.setKeyframe(node)


def get_relative_matrix(self, refMx, inMx):
    refMMx=list_to_matrix(refMx)
    inMMx=list_to_matrix(inMx)
    outMMx=inMMx * refMMx.inverse()
    outMx=matrix_to_list(outMMx)
    return outMx


def yup2zup(scale=1 ):
    x = [1.0, 0.0, 0.0, 0.0]
    y = [0.0, 0.0, 1.0, 0.0]
    z = [0.0,-1.0, 0.0, 0.0]
    w = [0.0, 0.0, 0.0, 1.0]
    m2m = list_to_matrix( x + y + z + w )
    m2m *= scale
    return m2m


def zup2yup(scale=1 ):
    x = [ 1.0, 0.0, 0.0, 0.0 ]
    y = [ 0.0, 0.0,-1.0, 0.0 ]
    z = [ 0.0, 1.0, 0.0, 0.0 ]
    w = [ 0.0, 0.0, 0.0, 1.0 ]
    m2m = list_to_matrix( x + y + z + w )
    m2m *= scale
    return m2m


def preNuMtx(scale=1 ):
    x = [ 1.0, 0.0, 0.0, 0.0 ]
    y = [ 0.0, 0.0, 1.0, 0.0 ]
    z = [ 0.0, 1.0, 0.0, 0.0 ]
    w = [ 0.0, 0.0, 0.0, 1.0 ]
    m2m = list_to_matrix( x + y + z + w )
    m2m *= scale
    return m2m


def postNuMtx(scale=1 ):
    x = [ -1.0, 0.0, 0.0, 0.0 ]
    y = [ 0.0, 1.0, 0.0, 0.0 ]
    z = [ 0.0, 0.0, 1.0, 0.0 ]
    w = [ 0.0, 0.0, 0.0, 1.0 ]
    m2m = list_to_matrix( x + y + z + w )
    m2m *= scale
    return m2m


class NuCamIO():
    """
    Nu Design Camera IO Class
    written by Robert Moggach, 2018
    This class provides functionality to import and export
    camera animation channels from NuDesign to Maya and back
    """

    def __init__(self):
        self.currentTime=cmds.currentTime(q=1)
        self.name = "NuCamIOWin"
        self.title = "Nu Design Camera Import"
        self.anim_start = 1001
        self.anim_end = 10000
        self.anim_step = 4
        self.legacy_offset = False
        self.legacy_rot = False
        self.camera = []
        self.animation = []
        self.offset = []
        self.actors = {}
        self.show_gui()

    def show_gui(self):
        self.build_gui()

    def build_gui(self):
        # check if window exists and delete window and/or prefs
        if cmds.window('nuCamIOWin', exists=True):
            cmds.deleteUI('nuCamIOWin', window=True)
        if cmds.windowPref('nuCamIOWin', exists=True):
            cmds.windowPref('nuCamIOWin',edit=True,widthHeight=[10,10])
        #initialize window
        self.window = cmds.window('nuCamIOWin',title="NuCamIO", iconName='NuCamIO', width=300, height=200)
        self.column = cmds.columnLayout(adjustableColumn=True)
        # create main title
        self.title = cmds.text('nuCamIOTitle', label='Nu Design Camera Import', backgroundColor=(0.18,0.18,0.18), height=50 )
        cmds.setParent( self.column )
        # create frame offset form
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), height=40, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 5), (2, 'both', 5)])
        cmds.text( label='Frame Start', align='center')
        self.anim_start_field = cmds.intField( 'animStart', value=1001, enable=True, height=30, changeCommand=self.set_anim_start)
        cmds.setParent( self.column )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), height=40, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 5), (2, 'both', 5)])
        cmds.text( label='Frame Step', align='center')
        self.anim_step_field = cmds.intField( 'animStep', value=4, enable=True, height=30, changeCommand=self.set_anim_step)
        cmds.setParent( self.column )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), height=40, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 5), (2, 'both', 5)])
        cmds.text( label='Legacy Offset?', align='center')
        self.legacy_offset = cmds.checkBox('legacy_offset', label='', value=False, cc=self.toggle_legacy_offset)
        cmds.setParent( self.column )
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), height=40, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 5), (2, 'both', 5)])
        cmds.text( label='Legacy Rotation?', align='center')
        self.legacy_offset = cmds.checkBox('legacy_rot', label='', value=False, cc=self.toggle_legacy_rot)
        cmds.setParent( self.column )
        # create actor column
        self.actorColumn = cmds.columnLayout(adjustableColumn=True, visible=False)
        self.actorList = cmds.textScrollList(visible=True, allowMultiSelection=False, isObscured=False, height=100, highlightColor=(0.5,0.5,0.5))
        cmds.setParent( self.column )
        # create help text
        self.help = cmds.text('nuCamIOStatus', label='Click "Import" to select JSON file', backgroundColor=(0.18,0.18,0.18), height=50 )
        cmds.setParent( self.column )
        # create import button row
        self.importRow = cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), rowAttach=(5, 'both', 5))
        cmds.button( 'nuCamIOImBtn', label="Import", height=50, width=150, command=self.import_data )
        cmds.button( 'nuCamIOCloseBtn', label='Close', height=50, width=150, command=self.closeWindow )
        cmds.setParent( self.column )
        # create locator buttons
        self.locatorRow = cmds.rowLayout(numberOfColumns=2, columnWidth2=(150,150), rowAttach=(5, 'both', 5), visible=False)
        cmds.button( 'nuCamIOImBtn', label="Create Locator", height=50, width=150, command=self.create_locators )
        cmds.button( 'nuCamIOCancelBtn', label='Close', height=50, width=150, command=self.closeWindow )
        cmds.setParent( self.column )
        # show window
        cmds.showWindow(self.window)

    def toggle_legacy_offset(self, *args):
        self.legacy_offset= not self.legacy_offset

    def toggle_legacy_rot(self, *args):
        self.legacy_rot= not self.legacy_rot

    def closeWindow(self, *args):
        cmds.deleteUI('nuCamIOWin', window=True)

    def set_anim_start(self, *args):
        self.anim_start = cmds.intField( self.anim_start_field, query=True, value=True)

    def set_anim_step(self, *args):
        self.anim_step = cmds.intField( self.anim_step_field, query=True, value=True)

    def get_json_file(self, *args):
        file_filters = "JSON File (*.json);;All Files (*.*)"
        caption = "Import JSON File"
        filename = cmds.fileDialog2(fileFilter=file_filters, dialogStyle=2, fileMode=1, caption=caption)
        self.filename=filename[0].encode('latin-1', 'replace')
        self.basename=os.path.basename(self.filename).split('.')[0]

    def refresh_actor_list(self):
        cmds.columnLayout(self.actorColumn,edit=True,visible=True)
        cmds.textScrollList(self.actorList, edit=True, removeAll=True)
        for key in sorted(self.actors.iterkeys()):
            listItem="{} | {}".format(key, self.actors[key]["AVName"])
            cmds.textScrollList(self.actorList, edit=True, append=listItem, uniqueTag=key)
        cmds.rowLayout(self.importRow,edit=True,visible=False)
        cmds.rowLayout(self.locatorRow,edit=True,visible=True)
        self.help = cmds.text(self.help, edit=True, label='Select actor to use as reference offset (or None)\n and click "Create Locator"')

    def create_locators(self,*args):
        ATTRS=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ']

        cmds.currentTime(self.anim_start,edit=True)
        currentTime=cmds.currentTime(query=True)

        self.group=cmds.group(empty=True,name="{}".format(self.basename))
        # offset
        self.offset_loc = cmds.spaceLocator()
        cmds.parent(self.offset_loc, self.group)
        self.offset_loc = cmds.rename(self.offset_loc, "world")
        self.offset_loc_offset = cmds.spaceLocator()
        cmds.parent(self.offset_loc_offset, self.offset_loc)
        self.offset_loc_offset = cmds.rename(self.offset_loc_offset, "world_offset")
        # anim offset - legacy attempt at stuff
        # self.anim_offset = cmds.spaceLocator()
        # cmds.parent(self.anim_offset, self.group)
        # self.anim_offset = cmds.rename(self.anim_offset, "anim_offset")
        # anim
        self.anim_loc = cmds.spaceLocator()
        cmds.parent(self.anim_loc, self.group)
        self.anim_loc = cmds.rename(self.anim_loc, "anim")

        self.anim_loc_offset = cmds.spaceLocator()
        cmds.parent(self.anim_loc_offset, self.anim_loc)
        self.anim_loc_offset = cmds.rename(self.anim_loc_offset, "anim_offset")

        # self.polyCone=cmds.polyCone( sx=10, sy=15, sz=5, r=5, h=20)
        # cmds.parent(self.polyCone,self.anim_loc_offset)

        for anim_frame in self.animation:
            cmds.select(self.anim_loc)
            mtx = preNuMtx() * list_to_matrix(get_matrix_from_ue4(anim_frame)) * list_to_matrix(get_matrix_from_ue4(self.offset)) * postNuMtx()
            cmds.xform(ws=True,m=matrix_to_list(mtx))

            for attr in ATTRS:
                cmds.setKeyframe(at=attr)
            currentTime+=self.anim_step
            cmds.currentTime(currentTime,edit=True)
        self.anim_end=currentTime
        cmds.playbackOptions(edit=True,animationEndTime=self.anim_end,maxTime=self.anim_end,animationStartTime=self.anim_start,minTime=self.anim_start)
        cmds.currentTime(self.anim_start,edit=True)

        selected_item = cmds.textScrollList(self.actorList, query=True, selectUniqueTagItem=True)
        if selected_item:
            cmds.select(self.offset_loc)
            translation=[self.actors[selected_item[0]]["Transform"]["Location"][chan] for chan in ["locationX","locationY","locationZ"]]
            rotation=[self.actors[selected_item[0]]["Transform"]["Rotation"][chan] for chan in ["roll","pitch","yaw"]]
            scale=[self.actors[selected_item[0]]["Transform"]["Scale"][chan] for chan in ["locationX","locationY","locationZ"]]

            mtx_list = get_matrix_from_ue4([translation,rotation,scale])
            mtx = preNuMtx() * list_to_matrix(mtx_list) * postNuMtx()

            cmds.xform(ws=True,m=matrix_to_list(mtx))
            for attr in ATTRS:
                cmds.setKeyframe(at=attr)

        self.closeWindow()
        #
        # ref_matrix = self.get_matrix_for_node(self.offset)
        # src_matrix = self.get_matrix_for_node(self.anim_loc)
        # off_matrix = self.get_relative_matrix(ref_matrix,src_matrix)
        # cmds.select(self.group)
        # self.locator = cmds.spaceLocator()
        # for active_frame in range(int(self.anim_start),int(self.anim_end),int(self.anim_step)):
        #     cmds.currentTime(active_frame,edit=True)
        #     self.apply_matrix_list(off_matrix,self.locator)

    def cleanup_animation(self,anim):
        track = "Track 0"
        animation = []
        current_time = 0.0
        translation_order = [0,1,2]
        # old
        rotation_order = [2,0,1]
        # updated
        # rotation_order = [1,2,0]
        offset_translation=[0,0,0]
        offset_rotation=[0,0,0]
        offset_scale=[1,1,1]
        if self.legacy_offset:
            offset_translation = [ float(i) for i in [anim[track]["OriginalTransform"]["Location"][loc] for loc in ["locationX","locationY","locationZ"]] ]
            offset_rotation =  [ float(i) for i in [anim[track]["OriginalTransform"]["Rotation"][rot] for rot in ["roll","pitch","yaw"]] ]
            offset_scale = [ float(i) for i in [anim[track]["OriginalTransform"]["Scale"][scale] for scale in ["locationX","locationY","locationZ"]] ]
        # offset_rotation = [ offset_rotation[i] for i in rotation_order]
        self.offset = [offset_translation, offset_rotation, offset_scale]
        print self.offset
        frame_data_dict = {}

        for frame_data in anim[track]["FrameData"].items():
            # translate the data
            frame=int(frame_data[0].replace("Frame ",""))
            translation,rotation,scale = [f.split(",") for f in frame_data[1]["FrameTransform"].split("|")]
            translation = [float(i) for i in translation]
            rotation = [float(i) for i in rotation]
            if self.legacy_rot:
                rotation = [ rotation[i] for i in rotation_order]
            scale = [float(i) for i in scale]
            translation = [ translation[i] for i in translation_order]
            # set the frame data
            frame_data_dict[frame]=[translation,rotation,scale]
        return [transform for (frame,transform) in sorted(frame_data_dict.items())]

    def import_data(self, *args):
        self.get_json_file()
        self.data=json.load(open(self.filename, 'r'))
        for key,val in self.data.items():
            if key == "Animation":
                self.animation = self.data[key]
            if key[0:5] == "Actor":
                if self.data[key]['Type'] == "Camera":
                    self.camera = self.data[key]
                if self.data[key]['Type'] == "AtomView":
                    niceKey="%s%03d" % (key.split(" ")[0],int(key.split(" ")[1]))
                    self.actors[niceKey]=val
        self.refresh_actor_list()
        self.animation = self.cleanup_animation(self.animation)

NuCamIO=NuCamIO()
