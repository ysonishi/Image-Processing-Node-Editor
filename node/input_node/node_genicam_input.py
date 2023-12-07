#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import time
import numpy as np
import dearpygui.dearpygui as dpg
from harvesters.core import Harvester

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node_editor.util import bayer_to_rgb, convert_cv_to_dpg

class Node(DpgNodeABC):
    _ver = '0.0.1'
    node_label = 'GenICam'
    node_tag = 'GenICam'
    _harvester = None
    _opencv_setting_dict = None

    def __init__(self):
        # Initialize the Harvester
        self._harvester = Harvester()

        # Load the GenTL Producer (Camera driver's GenTL Producer .cti file)
        gentl_path =os.environ['GENICAM_GENTL64_PATH']
        for file in os.listdir(gentl_path):
            if file.endswith(".cti"):
                self._harvester.add_file(os.path.join(gentl_path, file))
        self._harvester.update()
        self.device_id_list = []
        self.camera_instance_list = [] 
        self.camera_instance = None
        

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        # Tag name
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_name = tag_node_name + ':' + self.TYPE_INT + ':Input01'
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        tag_node_output01_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02'
        tag_node_output02_value_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # Setting for OpenCV
        self._opencv_setting_dict = opencv_setting_dict
        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        device_no_list = self._opencv_setting_dict['device_no_list']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Initialize black image
        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        # Register texture
        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # node
        with dpg.node(
                tag=tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            # Select camera no, combo box
            with dpg.node_attribute(
                    tag=tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    device_no_list,
                    width=small_window_w - 100,
                    label="Device No",
                    tag=tag_node_input01_value_name,
                )
            # camera image
            with dpg.node_attribute(
                    tag=tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(tag_node_output01_value_name)
            # processing time
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return tag_node_name

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value01_tag = tag_node_name + ':' + self.TYPE_INT + ':Input01Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        # device_id_list = self._opencv_setting_dict['device_id_list']
        # camera_instance_list = self._opencv_setting_dict['camera_instance_list']
        small_window_w = self._opencv_setting_dict['input_window_width']
        small_window_h = self._opencv_setting_dict['input_window_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # get camera id
        # camera_id = dpg_get_value(input_value01_tag)
        camera_id = 0

        if camera_id != '' and self.camera_instance == None :
            camera_id = int(camera_id)
            self.camera_instance = self._harvester.create(0)
            # camera_index = device_id_list.index(camera_id)
            # camera_instance = camera_instance_list[camera_index]

        # start measurement
        if camera_id != '' and use_pref_counter:
            start_time = time.perf_counter()

        # acquire image
        frame = None
        if self.camera_instance is not None:
            self.camera_instance.start()
            component = self.camera_instance.fetch().payload.components[0]
            bayer_frame = component.data.reshape(component.height, component.width)
            frame = bayer_to_rgb(bayer_frame)

            self.camera_instance.stop()

        # stop measurement
        if camera_id != '' and use_pref_counter:
            elapsed_time = time.perf_counter() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag,
                          str(elapsed_time).zfill(4) + 'ms')
        # display image
        if frame is not None:
            texture = convert_cv_to_dpg(
                frame,
                small_window_w,
                small_window_h,
            )
            dpg_set_value(output_value01_tag, texture)
        return frame, None

    def close(self, node_id):
        self._harvester.reset() # Release the resources.

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass