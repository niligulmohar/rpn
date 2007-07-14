# -*- coding: utf-8 -*-

# Authors:
#   Nicklas Lindgren <nili@lysator.liu.se>
#
# Copyright 2007 Nicklas Lindgren
#
# Released under GNU GPL, read the file 'COPYING' for more information

import pygame as py
from itertools import chain

######################################################################

def log(text):
    print text

try:
    import psyco
    psyco.full()
except:
    log('Psyco finns inte.')

######################################################################

class Button(object):
    def __init__(self):
        self.state = False
        self.last_push_time = -1000
        self.triggered = False
    def set(self, state):
        self.state = state
        if state:
            self.last_push_time = py.time.get_ticks()
            self.triggered = True
    def maybe_set(self, state):
        if state != self.state:
            self.set(state)
    def get_triggered(self):
        if self.triggered:
            self.triggered = False
            return True
        else:
            return False
    def __call__(self):
        return self.state

class Axis(object):
    THRESHOLD = 0.66
    def __init__(self, button_low, button_high):
        self.button_low = button_low
        self.button_high = button_high
    def set(self, value):
        if value < -self.THRESHOLD:
            self.button_low.maybe_set(True)
            self.button_high.maybe_set(False)
        elif value > self.THRESHOLD:
            self.button_low.maybe_set(False)
            self.button_high.maybe_set(True)
        else:
            self.button_low.maybe_set(False)
            self.button_high.maybe_set(False)

class Joystick(object):
    def __init__(self, joy):
        self.joystick = joy
        self.name = joy.get_name()
        joy.init()
        if joystick_maps.has_key(self.name):
            self.bindings = joystick_maps[self.name]
        elif joy.get_numaxes() < 2:
            print 'För få axlar (%d st) på joystick: %s' % (joy.get_numaxes(), self.name)
            joy.quit()
        elif joy.get_numbuttons() < 4:
            print 'För få knappar (%d st) på joystick: %s' % (joy.get_numbuttons(), self.name)
            joy.quit()
        else:
            print 'Känner inte igen joystick: %s' % self.name
            joy.quit()

reverse_keymap = {}
for key in (k for k in dir(py) if k[0:2] == 'K_'):
    code = getattr(py, key)
    reverse_keymap[code] = 'pygame.' + key

######################################################################

class View(object):
    def __init__(self, surface, *args):
        self.surface = surface
        self.init(*args)
    def init(*args):
        pass
    def update(self):
        pass

######################################################################

class Controller(object):
    def __init__(self, view, *args):
        self.inputs = {}
        self.view = view
        self.target_fps = 30
        self.running = True
        self.keymap = {}
        self.keymap_select_map = {}
        self.joysticks = []
        self.init(*args)
    def set_keymaps(self, keymap_alts):
        self.keymap = keymap_alts[0]
        self.last_used_map = self.keymap

        self.keymap_select_map = {}

        class DuplicateKey(Exception):
            pass

        for cur_keymap in keymap_alts:
            for key in cur_keymap.keys():
                try:
                    cmp_keymap_alts = keymap_alts[:]
                    cmp_keymap_alts.remove(cur_keymap)
                    if not key in chain((k.keys for k in keymap_alts)):
                        self.keymap_select_map[key] = cur_keymap
                except DuplicateKey:
                    pass
        
    def init(*args):
        pass
    def before_frame(self):
        pass
    def after_frame(self):
        pass
    def update_inputs(self):
        for event in py.event.get():
            if event.type == py.KEYDOWN:
                ######################################################
                if event.key == py.K_ESCAPE:
                    self.running = False
                elif event.key == py.K_RETURN and event.mod:
                    py.display.toggle_fullscreen()
                elif self.keymap.has_key(event.key):
                        self.keymap[event.key].set(True)
                elif self.keymap_select_map.has_key(event.key):
                    self.keymap = self.keymap_select_map[event.key]
                    log('Magiskt keymapbyte till: %s' % keymap['name'])
                    self.keymap[event.key].set(True)
                else:
                    if reverse_keymap.has_key(event.key):
                        name = reverse_keymap[event.key]
                    else:
                        name = '%d' % event.key
                    log('Obunden tangent: %s' % name)
            elif event.type == py.KEYUP:
                if self.keymap.has_key(event.key):
                    self.keymap[event.key].set(False)
            elif event.type == py.JOYBUTTONDOWN:
                buttons = self.joysticks[event.joy].bindings['buttons']
                if buttons.has_key(event.button):
                    buttons[event.button].set(True)
                else:
                    log('Obunden knapp %d på %s' % (event.button, joysticks[event.joy].name))
            elif event.type == py.JOYBUTTONUP:
                buttons = self.joysticks[event.joy].bindings['buttons']
                if buttons.has_key(event.button):
                    buttons[event.button].set(False)
            elif event.type == py.JOYAXISMOTION:
                axes = self.joysticks[event.joy].bindings['axes']
                if axes.has_key(event.axis):
                    axes[event.axis].set(event.value)
                else:
                    log('Obunden axel %d på %s' % (event.axis, joysticks[event.joy].name))
    def event_loop(self):
        clock = py.time.Clock()
        first_frame = True
        while (self.running):
            if first_frame:
                py.event.get()
                first_frame = False
            else:
                self.update_inputs()
            self.before_frame()
            self.view.update()
            self.after_frame()
            clock.tick(self.target_fps)
