#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Authors:
#   Nicklas Lindgren <nili@lysator.liu.se>
#
# Copyright 2007 Nicklas Lindgren
#
# Released under GNU GPL, read the file 'COPYING' for more information

import game
import os.path, math, random
from OpenGL.GL import *
from OpenGL.GLU import *

######################################################################

files = {}

def index_directory(none, directory, filenames):
    if directory.count(".svn") == 0:
        for f in filenames:
            files[f] = os.path.join(directory, f)

os.path.walk('data', index_directory, None)

class Texture(object):
    def __init__(self, filename = None, outline_of = None):
        self.surface = None
        if filename:
            self.surface = game.py.image.load(files[filename]).convert_alpha()
        elif outline_of:
            self.surface = outline_of.surface.copy()
            for y in [-1, 0, 1]:
                for x in [-1, 0, 1]:
                    self.surface.blit(outline_of.surface, [x, y])
        if not self.surface:
            raise 'Parameter saknas'
        self.opengl_name = glGenTextures(1)
        width = self.surface.get_width()
        height = self.surface.get_height()
        self.bind()
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, game.py.image.tostring(self.surface, "RGBA", 0) )
    def bind(self):
        glBindTexture( GL_TEXTURE_2D, self.opengl_name )

######################################################################

class Model(object):
    def __init__(self):
        self.frames = 0
        self.robots = [Robot()]
    def before_frame(self):
        self.frames += 1
        self.robots[0].act_on_inputs(self.move_up, self.move_down, self.move_left, self.move_right, self.action)

class Entity(object):
    VELOCITY = 2.5
    SQRT2 = 1 / math.sqrt(2)
    def __init__(self):
        self.x = 0
        self.y = 0

class Robot(Entity):
    def __init__(self):
        Entity.__init__(self)
    def act_on_inputs(self, up, down, left, right, action):
        if up() and not down():
            self.dy = -1
        elif down() and not up():
            self.dy = 1
        else:
            self.dy = 0
        if left() and not right():
            self.dx = -1
        elif right() and not left():
            self.dx = 1
        else:
            self.dx = 0
        if self.dx and self.dy:
            self.dx *= self.SQRT2
            self.dy *= self.SQRT2
        self.dx *= self.VELOCITY
        self.dy *= self.VELOCITY
        self.x += self.dx
        self.y += self.dy

######################################################################

class BodyPart(object):
    @classmethod
    def class_init(cls):
        cls.sprites = {}
        for n in ['torso1', 'arm1', 'leg_l1', 'leg_r1', 'head1', 'eye1', 'pupil1']:
            cls.sprites[n] = Texture(filename = n + '.png')
            cls.sprites[n].outline = Texture(outline_of = cls.sprites[n])

    def __init__(self, texture, color, parent = None):
        self.animation_speed_factor = 1.0/13
        self.visible = True
        self.size = 16
        self.texture = texture
        self.outline_texture = texture.outline
        self.color = color
        self.outline_color = [0,0,0,1]
        self.pos0 = [0,0]
        self.pos = [0,0]
        self.current_pos = self.pos[:]
        self.rot0 = 0
        self.rot = 0
        self.current_rot = self.rot
        self.rot_factor = 1
        self.children = []
        if parent:
            parent.children.append(self)
    def draw(self):
        self.draw_layer(0)
        self.draw_layer(1)
    def draw_layer(self, layer):
        if self.visible:
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            self.current_pos[0] += (self.pos[0] - self.current_pos[0]) * self.animation_speed_factor
            self.current_pos[1] += (self.pos[1] - self.current_pos[1]) * self.animation_speed_factor
            self.current_rot += (self.rot - self.current_rot) * self.animation_speed_factor
            glTranslatef(self.pos0[0] + self.current_pos[0], self.pos0[1] + self.current_pos[1], 0)
            glRotatef(self.rot0 + self.current_rot * self.rot_factor, 0, 0, 1)
    
            c, t = ((self.outline_color, self.outline_texture),
                    (self.color, self.texture))[layer]
            t.bind()
            glBegin(GL_QUADS)
            glColor4fv(c)
            glTexCoord2f(0,0)
            glVertex2f(-self.size, -self.size)
            glTexCoord2f(1,0)
            glVertex2f(self.size, -self.size)
            glTexCoord2f(1,1)
            glVertex2f(self.size, self.size)
            glTexCoord2f(0,1)
            glVertex2f(-self.size, self.size)
            glEnd()
            for c in self.children:
                c.draw_layer(layer)
            glPopMatrix()


class RobotSprite(object):
    PUPIL_FACTOR = 2 / Robot.VELOCITY
    def __init__(self, entity, color):
        self.entity = entity
        self.color = color
        self.dance = False
        self.moving = False
        self.move_up_down_phase = 0
        self.move_left_right_sign = 1
        self.look_delay = 0
        self.new_look_delay()
        self.gesture_delay = 0
        self.new_gesture_delay()
        self.blink_delay = 0
        self.new_blink_delay()

        self.body = BodyPart(BodyPart.sprites['torso1'], color)
        self.head = BodyPart(BodyPart.sprites['head1'], color, self.body)
        self.head.pos0[1] = -4
        self.eye_l = BodyPart(BodyPart.sprites['eye1'], [1,1,1,1], self.head)
        self.eye_l.pos0 = [-4, -7]
        self.pupil_l = BodyPart(BodyPart.sprites['pupil1'], [0,0,0,1], self.eye_l)
        self.pupil_l.animation_speed_factor = 0.5
        self.eye_r = BodyPart(BodyPart.sprites['eye1'], [1,1,1,1], self.head)
        self.eye_r.pos0 = [4, -7]
        self.pupil_r = BodyPart(BodyPart.sprites['pupil1'], [0,0,0,1], self.eye_r)
        self.pupil_r.animation_speed_factor = 0.5
        self.arm_r = BodyPart(BodyPart.sprites['arm1'], color, self.body)
        self.arm_r.pos0 = [6, -1]
        self.arm_r.rot = 30
        self.arm_r.current_rot = 30
        self.arm_l = BodyPart(BodyPart.sprites['arm1'], color, self.body)
        self.arm_l.pos0 = [-6, -1]
        self.arm_l.rot0 = 180
        self.arm_l.rot_factor = -1
        self.arm_l.rot = 30
        self.arm_l.current_rot = 30
        self.leg_r = BodyPart(BodyPart.sprites['leg_r1'], color, self.body)
        self.leg_r.pos0 = [4,4]
        self.leg_l = BodyPart(BodyPart.sprites['leg_l1'], color, self.body)
        self.leg_l.pos0 = [-4,4]
    def new_look_delay(self):
        self.look_delay += int(random.random() * 42) + 23
    def new_gesture_delay(self):
        self.gesture_delay += int(random.random() * 600) + 60
    def new_blink_delay(self):
        self.blink_delay += int(random.random() * 10) + 60
    def draw(self, frame):
        self.body.pos0[0] = self.entity.x
        self.body.pos0[1] = self.entity.y
        if self.entity.dx or self.entity.dy:
            if not self.moving:
                self.moving = True
                self.move_up_down_phase = 0
            self.move_up_down_phase += 1
            if not self.entity.dy:
                self.move_left_right_sign = self.entity.dx / abs(self.entity.dx)
        elif self.moving:
            self.move_up_down_phase = 0
            self.moving = False
            self.dance = False
            self.new_gesture_delay()
                
        sideways_l = sideways_r = height_l = height_r = 0
        if self.moving:
            arm_angle = -40
            torso_height = 0
            self.dance = False
            height_l = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][self.move_up_down_phase % 12] * Robot.VELOCITY
            height_r = - height_l
            if not self.entity.dy:
                height_l = min(height_l, 2)
                height_r = min(height_r, 2)
                sideways_l = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][(self.move_up_down_phase + 3) % 12] * Robot.VELOCITY * self.move_left_right_sign
                sideways_r = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][(self.move_up_down_phase + 9) % 12] * Robot.VELOCITY * self.move_left_right_sign
        elif self.dance:
            arm_angle = math.sin(frame * 0.1) * 30
            torso_height = math.cos(frame * 0.2) * 1
        else:
            arm_angle = 30
            torso_height = 0
        self.arm_r.rot = self.arm_l.rot = arm_angle
        self.body.pos[1] = torso_height
        self.leg_l.pos[0] = sideways_l
        self.leg_r.pos[0] = sideways_r
        self.leg_l.pos[1] = -torso_height + height_l
        self.leg_r.pos[1] = -torso_height + height_r
        if self.moving:
            self.pupil_l.pos = self.pupil_r.pos = [self.entity.dx * self.PUPIL_FACTOR,
                                                   self.entity.dy * self.PUPIL_FACTOR]
        elif frame >= self.look_delay:
            self.new_look_delay()
            if random.random() > 0.1:
                angle = random.random() * math.pi * 2
                x = math.cos(angle) * 2
                y = math.sin(angle) * 2
            else:
                x = y = 0
            self.pupil_l.pos = [x, y]
            self.pupil_r.pos = [x, y]
        if frame >= self.gesture_delay:
            self.new_gesture_delay()
            self.dance = not self.dance
        if self.entity.dy < 0:
            self.eye_r.visible = False
            self.eye_l.visible = False
        elif frame >= self.blink_delay:
            self.new_blink_delay()
            self.eye_r.visible = True
            self.eye_l.visible = True
        elif frame >= self.blink_delay - 3:
            self.eye_r.visible = False
            self.eye_l.visible = False
        else:
            self.eye_r.visible = True
            self.eye_l.visible = True
        self.body.draw()

class RpnView(game.View):
    CLEAR_COLOR = [0.28, 0.24, 0.55, 0.0]
    def init(self, model):
        self.model = model
        self.robot = RobotSprite(model.robots[0], [0.6,0.2,0.2,1])

    def update(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(-WIDTH/2, WIDTH/2, HEIGHT/2, -HEIGHT/2)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glClearColor(*self.CLEAR_COLOR)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


        glScalef(*([2]*3))
        self.robot.draw(self.model.frames)
        game.py.display.flip()


######################################################################

class RpnController(game.Controller):
    def init(self, model):
        self.model = model
        model.move_up = game.Button()
        model.move_down = game.Button()
        model.move_left = game.Button()
        model.move_right = game.Button()
        model.action = game.Button()
        self.pause = game.Button()
        self.inputs = [model.move_up, model.move_down, model.move_left, model.move_right, model.action]
        self.set_keymaps([{ 'name': 'Standardbindningar',
                            game.py.K_KP8: model.move_up,
                            game.py.K_KP2: model.move_down,
                            game.py.K_KP4: model.move_left,
                            game.py.K_KP6: model.move_right,
                            game.py.K_UP: model.move_up,
                            game.py.K_DOWN: model.move_down,
                            game.py.K_LEFT: model.move_left,
                            game.py.K_RIGHT: model.move_right,
                            game.py.K_LCTRL: model.action,
                            game.py.K_LALT: model.action,
                            game.py.K_SPACE: model.action,
                            game.py.K_LSHIFT: model.action,
                            game.py.K_z: model.action,
                            game.py.K_x: model.action,
                            game.py.K_1: self.pause,
                            game.py.K_p: self.pause,
                            game.py.K_PAUSE: self.pause }])
   
    def before_frame(self):
        self.model.before_frame()

######################################################################

game.py.init()

WIDTH, HEIGHT = (1024, 768)
flags = game.py.DOUBLEBUF | game.py.OPENGL
if max(game.py.display.list_modes()) <= (WIDTH, HEIGHT):
    flags |= game.py.FULLSCREEN | game.py.HWSURFACE
screen = game.py.display.set_mode((WIDTH, HEIGHT), flags)
game.py.mouse.set_visible(True)

BodyPart.class_init()

model = Model()
view = RpnView(screen, model)
controller = RpnController(view, model)

controller.event_loop()

game.py.quit()

######################################################################
