# -*- coding: utf-8 -*-

# Authors:
#   Nicklas Lindgren <nili@lysator.liu.se>
#
# Copyright 2007 Nicklas Lindgren
#
# Released under GNU GPL, read the file 'COPYING' for more information

import pygame as py
from itertools import chain
import random

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

SOUND = True
END_MUSIC_EVENT = py.USEREVENT

class Music(object):
    class Song(object):
        def __init__(self, name, bpm, bpb, intro_delay_bars = 0, intro_delay_s = 0):
            self.name = name
            self.bpm = bpm
            self.bpb = bpb
            self.intro_delay_bars = intro_delay_bars
            self.intro_delay_ticks = intro_delay_s * 1000
        def play(self):
            py.mixer.music.stop()
            py.mixer.music.load(self.name)
            py.mixer.music.play(0)
            py.mixer.music.set_endevent(END_MUSIC_EVENT)
        def bars(self, ticks):
            return (ticks - self.intro_delay_ticks - EXPECTED_MUSIC_DELAY) / 60000.0 * self.bpm / self.bpb - self.intro_delay_bars
        def beats(self, ticks):
            return (ticks - self.intro_delay_ticks - EXPECTED_MUSIC_DELAY) / 60000.0 * self.bpm - (self.intro_delay_bars * self.bpb)

    songs = {}

    def __init__(self):
        self.volume = 1.0
        self.current_song = None
        self.playlist = self.songs.values()
        self.stopped = True
        random.shuffle(self.playlist)
    def next(self):
        if not self.stopped:
            self.play()
    def play(self, song = None):
        if not song:
            #song = random.choice(self.songs.values())
            song = self.playlist[0]
        else:
            song = self.songs[song]
        self.playlist.remove(song)
        self.playlist.append(song)
        self.current_song = song
        self.song_start_ticks = py.time.get_ticks()
        self.stopped = False
        py.mixer.music.set_volume(self.volume)
        if SOUND:
            song.play()

    def stop(self):
        self.current_song = None
        self.stopped = True
        if SOUND:
            py.mixer.music.fadeout(7000)
    def pause(self):
        self.pause_ticks = py.time.get_ticks()
        if SOUND:
            py.mixer.music.pause()
    def unpause(self):
        now = py.time.get_ticks()
        self.song_start_ticks += now - self.pause_ticks
        if SOUND:
            py.mixer.music.unpause()
    def bars(self):
        if self.current_song:
            now = py.time.get_ticks()
            return self.current_song.bars(now - self.song_start_ticks)
        else:
            return 0
    def beats(self):
        if self.current_song:
            now = py.time.get_ticks()
            return self.current_song.beats(now - self.song_start_ticks)
        else:
            return 0
    

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
