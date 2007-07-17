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

######################################################################

class Texture(object):
    @classmethod
    def class_init(cls):
        def make_font(name, size):
            return game.py.font.Font(files[name + '.TTF'], size)
        cls.font = make_font('TEACPSSB', 8)
        cls.texts = {}
    # TODO: Låta bli att läcka text_surface:s
    @classmethod
    def text(cls, text):
        if cls.texts.has_key(text):
            return cls.texts[text]
        small_surface = cls.font.render(text, False, (255,255,255))
        texture_surface = game.py.Surface((2 ** int(math.ceil(math.log(small_surface.get_width()) / math.log(2))),
                                           2 ** int(math.ceil(math.log(small_surface.get_height()) / math.log(2)))),
                                          game.py.SRCALPHA, 32)
        texture_surface.blit(small_surface, (0,0))
        texture = Texture(surface = texture_surface)
        texture.text_width = float(small_surface.get_width() - 1) / texture_surface.get_width()
        texture.text_height = float(small_surface.get_height()) / texture_surface.get_height()
        cls.texts[text] = texture
        return texture
        
    def __init__(self, filename = None, outline_of = None, surface = None):
        self.surface = None
        if surface:
            self.surface = surface
        elif filename:
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
        self.grid = Grid()
        self.robots = [Robot(self.grid)]
        self.draw_map("""
  ###
### #########
#           #
# +         #
#       S   #
# ? ?       #
#           #
# + ? - ? + #
#           #
# ? ? + ? ? #
#           #
######### ###
        ###""")
    def before_frame(self):
        self.frames += 1
        self.robots[0].act_on_inputs(self.move_up, self.move_down, self.move_left, self.move_right, self.action)
    def draw_map(self, string):
        lines = string.split("\n")
        y0 = -len(lines) / 2
        x0 = -max((len(s) for s in lines)) / 2 + 1
        for yd, l in enumerate(lines):
            for xd, c in enumerate(l):
                x = x0+xd
                y = y0+yd
                self.grid.set(x, y, Cell(c == '#'))
                if c == 'S':
                    self.robots[0].move(x, y)
                elif c in "0123456789":
                    self.grid.get(x, y).object = Number(self.grid, ord(c) - ord("0"))
                elif c == '?':
                    self.grid.get(x, y).object = Number(self.grid, random.randrange(100))
                elif c == '!':
                    self.grid.get(x, y).object = Number(self.grid, random.randrange(1000))
                elif c in "+-*/":
                    self.grid.get(x, y).object = Operator(self.grid, c)
                    
                    
class Cell(object):
    def __init__(self, blocked = False):
        self.blocked = blocked
        self.object = None
    def has_action(self):
        return not self.blocked

class Grid(object):
    def __init__(self):
        self.rows = {}
        self.default_cell = Cell()

    def get(self, x, y):
        if self.rows.has_key(y):
            if self.rows[y].has_key(x):
                return self.rows[y][x]
        return self.default_cell
    def set(self, x, y, cell):
        if not self.rows.has_key(y):
            self.rows[y] = {}
        self.rows[y][x] = cell

class Entity(object):
    VELOCITY = 2.8 / 32
    CORNERING_VELOCITY = VELOCITY * 0.8
    SQRT2 = 1 / math.sqrt(2)
    def __init__(self, grid):
        self.x = 0
        self.y = 0
        self.grid = grid
    def occupied_grid_rows(self):
        fraction = self.y
        primary = round(fraction)
        difference = fraction - primary
        if difference == 0:
            return (primary, primary, 0)
        elif difference > 0:
            return (primary, primary + 1, difference)
        else:
            return (primary, primary - 1, difference)
    def occupied_grid_cols(self):
        fraction = self.x
        primary = round(fraction)
        difference = fraction - primary
        if difference == 0:
            return (primary, primary, 0)
        elif difference > 0:
            return (primary, primary + 1, difference)
        else:
            return (primary, primary - 1, difference)

def clamp(min_val, x, max_val):
    return max(min_val, min(x, max_val))

class Robot(Entity):
    MAX_STACK_HEIGHT = 11
    def __init__(self, grid):
        Entity.__init__(self, grid)
        self.target_x = 0
        self.target_y = 1
        self.target_dx = 0
        self.target_dy = 1
        self.stack = []
    def move(self, x, y):
        self.x = x
        self.y = y
        self.target_x = self.x + self.target_dx
        self.target_y = self.y + self.target_dy
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
        if self.dx or self.dy:
            self.target_dx = self.dx
            self.target_dy = self.dy
        if self.dx and self.dy:
            self.dx *= self.SQRT2
            self.dy *= self.SQRT2
        self.dx *= self.VELOCITY
        self.dy *= self.VELOCITY
        self.x += self.dx
        self.y += self.dy

        # TODO: Skriv om på ett snyggt och begripligt sätt:
        # TODO: Se även till så att den gör rätt i samtliga fall där man försöker gå diagonalt.
        self.rows = self.occupied_grid_rows()
        self.cols = self.occupied_grid_cols()

        def check_x():
            if self.dx:
                if self.grid.get(self.cols[1],self.rows[0]).blocked or self.grid.get(self.cols[1],self.rows[1]).blocked:
                    self.x = self.cols[0]
                    if self.dy == 0:
                        if not self.grid.get(self.cols[1],self.rows[0]).blocked:
                            self.y -= clamp(-Robot.CORNERING_VELOCITY, self.rows[2], Robot.CORNERING_VELOCITY)
                        elif not self.grid.get(self.cols[1],self.rows[1]).blocked:
                            self.y += clamp(-Robot.CORNERING_VELOCITY, self.rows[2], Robot.CORNERING_VELOCITY)
                    else:
                        self.cols = (self.cols[0], self.cols[0], 0)
                        
        def check_y():
            if self.dy:
                if self.grid.get(self.cols[0],self.rows[1]).blocked or self.grid.get(self.cols[1],self.rows[1]).blocked:
                    self.y = self.rows[0]
                    if self.dx == 0:
                        if not self.grid.get(self.cols[0],self.rows[1]).blocked:
                            self.x -= clamp(-Robot.CORNERING_VELOCITY, self.cols[2], Robot.CORNERING_VELOCITY)
                        elif not self.grid.get(self.cols[1],self.rows[1]).blocked:
                            self.x += clamp(-Robot.CORNERING_VELOCITY, self.cols[2], Robot.CORNERING_VELOCITY)
                    else:
                        self.rows = (self.rows[0], self.rows[0], 0)
        if abs(self.rows[2]) < abs(self.cols[2]):
            check_y()
            check_x()
        else:
            check_x()
            check_y()
        self.target_x = int(round(self.x) + self.target_dx)
        self.target_y = int(round(self.y) + self.target_dy)

        if action.get_triggered():
            target = self.grid.get(self.target_x, self.target_y)
            if not target.has_action():
                pass
            elif target.object:
                if not self.stack_full():
                    self.stack.append(target.object)
                    target.object.pushed_on(self.stack)
                    target.object = None
            elif not self.stack_empty():
                target.object = self.stack.pop()
            else:
                pass
    def stack_full(self):
        return len(self.stack) >= self.MAX_STACK_HEIGHT
    def stack_empty(self):
        return len(self.stack) == 0

class Number(Entity):
    def __init__(self, grid, numerator, denominator = 1):
        Entity.__init__(self, grid)
        self.numerator = numerator
        self.denominator = denominator
    def text_len(self):
        return len(str(self.numerator))
    def pushed_on(self, stack):
        pass

class Operator(Entity):
    def __init__(self, grid, operator_type = "+"):
        Entity.__init__(self, grid)
        self.operator_type = operator_type
    def text_len(self):
        return len(self.operator_type)
    def pushed_on(self, stack):
        if len(stack) >= 3:
            if isinstance(stack[-2], Number) and isinstance(stack[-3], Number):
                stack.pop()
                operand0 = stack.pop()
                operand1 = stack.pop()
                if self.operator_type == '+':
                    stack.append(Number(self.grid, operand1.numerator + operand0.numerator))
                elif self.operator_type == '-':
                    stack.append(Number(self.grid, operand1.numerator - operand0.numerator))
                elif self.operator_type == '*':
                    stack.append(Number(self.grid, operand1.numerator * operand0.numerator))
                elif self.operator_type == '/':
                    stack.append(Number(self.grid, float(operand1.numerator) / operand0.numerator))


######################################################################

class DampedValue(object):
    def __init__(self, value, difference_reduction = 1.0/13):
        self.set_immediately(value)
        self.difference_reduction = difference_reduction
    def set_target(self, value):
        self.target = value
    def set_immediately(self, value):
        self.current = value
        self.target = value
    def update(self):
        self.current += (self.target - self.current) * self.difference_reduction
    def __call__(self):
        return self.current

class BodyPart(object):
    @classmethod
    def class_init(cls):
        cls.sprites = {}
        for n in ['torso1', 'arm1', 'leg_l1', 'leg_r1', 'head1', 'eye1', 'pupil1', 'shadow']:
            cls.sprites[n] = Texture(filename = n + '.png')
            cls.sprites[n].outline = Texture(outline_of = cls.sprites[n])

    def __init__(self, texture, color, parent = None, outline = True):
        self.visible = True
        self.outline = outline
        self.size = 16
        self.texture = texture
        self.outline_texture = texture.outline
        self.color = color
        self.outline_color = [0,0,0,1]
        self.pos0 = [0,0]
        self.pos = [DampedValue(0), DampedValue(0)]
        self.rot0 = 0
        self.rot = DampedValue(0)
        self.rot_factor = 1
        self.children = []
        if parent:
            parent.children.append(self)
    def draw(self):
        self.draw_layer(0)
        self.draw_layer(1)
    def draw_layer(self, layer):
        if self.visible and ((layer == 0 and self.outline) or layer == 1):
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            self.pos[0].update()
            self.pos[1].update()
            self.rot.update()

            glTranslatef(self.pos0[0] + self.pos[0](), self.pos0[1] + self.pos[1](), 0)
            glRotatef(self.rot0 + self.rot() * self.rot_factor, 0, 0, 1)
    
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
        self.frame = 0
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
        self.shadow = BodyPart(BodyPart.sprites['shadow'], [0,0,0,1], self.body, False)
        self.shadow.pos0[1] = 2
        self.head = BodyPart(BodyPart.sprites['head1'], color, self.body)
        self.head.pos0[1] = -4
        self.eye_l = BodyPart(BodyPart.sprites['eye1'], [1,1,1,1], self.head, False)
        self.eye_l.pos0 = [-4, -7]
        self.pupil_l = BodyPart(BodyPart.sprites['pupil1'], [0,0,0,1], self.eye_l, False)
        self.pupil_l.pos[0].difference_reduction = 0.5
        self.pupil_l.pos[1].difference_reduction = 0.5
        self.eye_r = BodyPart(BodyPart.sprites['eye1'], [1,1,1,1], self.head, False)
        self.eye_r.pos0 = [4, -7]
        self.pupil_r = BodyPart(BodyPart.sprites['pupil1'], [0,0,0,1], self.eye_r, False)
        self.pupil_r.pos[0].difference_reduction = 0.5
        self.pupil_r.pos[1].difference_reduction = 0.5
        self.arm_r = BodyPart(BodyPart.sprites['arm1'], color, self.body)
        self.arm_r.pos0 = [6, -1]
        self.arm_r.rot.set_immediately(30)
        self.arm_l = BodyPart(BodyPart.sprites['arm1'], color, self.body)
        self.arm_l.pos0 = [-6, -1]
        self.arm_l.rot0 = 180
        self.arm_l.rot_factor = -1
        self.arm_l.rot.set_immediately(30)
        self.leg_r = BodyPart(BodyPart.sprites['leg_r1'], color, self.body)
        self.leg_r.pos0 = [4,4]
        self.leg_l = BodyPart(BodyPart.sprites['leg_l1'], color, self.body)
        self.leg_l.pos0 = [-4,4]
    def new_look_delay(self):
        self.look_delay = self.frame + int(random.random() * 42) + 23
    def new_gesture_delay(self):
        self.gesture_delay = self.frame + int(random.random() * 600) + 60
    def new_blink_delay(self):
        self.blink_delay = self.frame + int(random.random() * 10) + 60
    def draw(self):
        self.frame += 1
        self.body.pos0[0] = self.entity.x * Map.TILE_SIZE
        self.body.pos0[1] = self.entity.y * Map.TILE_SIZE
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
            height_l = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][self.move_up_down_phase % 12] * Robot.VELOCITY * Map.TILE_SIZE
            height_r = - height_l
            if not self.entity.dy:
                height_l = min(height_l, 2)
                height_r = min(height_r, 2)
                sideways_l = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][(self.move_up_down_phase + 3) % 12] * Robot.VELOCITY * Map.TILE_SIZE * self.move_left_right_sign
                sideways_r = [0,1,2,3,2,1,0,-1,-2,-3,-2,-1][(self.move_up_down_phase + 9) % 12] * Robot.VELOCITY * Map.TILE_SIZE * self.move_left_right_sign
        elif self.dance:
            arm_angle = math.sin(self.frame * 0.1) * 30
            torso_height = math.cos(self.frame * 0.2) * 1
        else:
            arm_angle = 30
            torso_height = 0
        self.arm_r.rot.set_target(arm_angle)
        self.arm_l.rot.set_target(arm_angle)
        self.body.pos[1].set_target(torso_height)
        self.leg_l.pos[0].set_target(sideways_l)
        self.leg_r.pos[0].set_target(sideways_r)
        self.leg_l.pos[1].set_target(-torso_height + height_l)
        self.leg_r.pos[1].set_target(-torso_height + height_r)
        self.shadow.pos[1].set_target(-torso_height)
        if self.moving:
            x = self.entity.dx * self.PUPIL_FACTOR
            self.pupil_l.pos[0].set_target(x)
            self.pupil_r.pos[0].set_target(x)
            y = self.entity.dy * self.PUPIL_FACTOR
            self.pupil_l.pos[1].set_target(y)
            self.pupil_r.pos[1].set_target(y)

        elif self.frame >= self.look_delay:
            self.new_look_delay()
            if random.random() > 0.1:
                angle = random.random() * math.pi * 2
                x = math.cos(angle) * 2
                y = math.sin(angle) * 2
            else:
                x = y = 0
            self.pupil_l.pos[0].set_target(x)
            self.pupil_l.pos[1].set_target(y)
            self.pupil_r.pos[0].set_target(x)
            self.pupil_r.pos[1].set_target(y)
        if self.frame >= self.gesture_delay:
            self.new_gesture_delay()
            self.dance = not self.dance
        if self.entity.dy < 0:
            self.eye_r.visible = False
            self.eye_l.visible = False
            self.head.pos[1].set_target(2)
        else:
            self.head.pos[1].set_target(0)
            if self.frame >= self.blink_delay:
                self.new_blink_delay()
                self.eye_r.visible = True
                self.eye_l.visible = True
            elif self.frame >= self.blink_delay - 3:
                self.eye_r.visible = False
                self.eye_l.visible = False
            else:
                self.eye_r.visible = True
                self.eye_l.visible = True
        self.body.draw()


class NumberSprite(object):
    @classmethod
    def class_init(cls):
        cls.sprites = {}
        for n in ['number_base', 'operator_base']:
            cls.sprites[n] = Texture(filename = n + '.png')
    @classmethod
    def color(cls, obj):
        if isinstance(obj, Operator):
            return (random.expovariate(13),
                    random.expovariate(17),
                    random.expovariate(13))
        else:
            return [(0.3, 0.3, 0.3),
                    (0.5, 0.3, 0.0),
                    (0.8, 0.0, 0.0),
                    (1.0, 0.5, 0.0),
                    (0.9, 0.9, 0.0),
                    (0.0, 0.8, 0.0),
                    (0.0, 0.0, 0.9),
                    (1.0, 0.0, 1.0),
                    (0.5, 0.5, 0.5),
                    (0.9, 0.9, 0.9)][abs(int(obj.numerator % 10))]
    @classmethod
    def draw(cls, obj):
        operator = isinstance(obj, Operator)
        if operator:
            NumberSprite.sprites['operator_base'].bind()
        else:
            NumberSprite.sprites['number_base'].bind()
        glBegin(GL_QUADS)
        glColor3f(*NumberSprite.color(obj))
        glTexCoord2f(0, 0)
        glVertex2f(-1, -1)
        glTexCoord2f(1, 0)
        glVertex2f(1, -1)
        glTexCoord2f(1, 1)
        glVertex2f(1, 1)
        glTexCoord2f(0, 1)
        glVertex2f(-1, 1)
        glEnd()
        if operator:
            t = Texture.text(obj.operator_type)
        else:
            t = Texture.text(str(obj.numerator))
        t.bind()
        glBegin(GL_QUADS)
        if obj.text_len() == 1:
            TEXT_WIDTH = 0.35
        else:
            TEXT_WIDTH = 0.7
        TEXT_HEIGHT = 0.9
        SHADOW_OFFSET = 0.1
        SHADOW_OFFSET_X = 0.05

        glColor4f(0,0,0,0.7)

        glTexCoord2f(0, 0)
        glVertex2f(-TEXT_WIDTH + SHADOW_OFFSET_X, -TEXT_HEIGHT + SHADOW_OFFSET)
        glTexCoord2f(t.text_width, 0)
        glVertex2f(TEXT_WIDTH + SHADOW_OFFSET_X, -TEXT_HEIGHT + SHADOW_OFFSET)
        glTexCoord2f(t.text_width, t.text_height)
        glVertex2f(TEXT_WIDTH + SHADOW_OFFSET_X, TEXT_HEIGHT + SHADOW_OFFSET)
        glTexCoord2f(0, t.text_height)
        glVertex2f(-TEXT_WIDTH + SHADOW_OFFSET_X, TEXT_HEIGHT + SHADOW_OFFSET)

        glColor4f(1,1,1,1)

        glTexCoord2f(0, 0)
        glVertex2f(-TEXT_WIDTH, -TEXT_HEIGHT)
        glTexCoord2f(t.text_width, 0)
        glVertex2f(TEXT_WIDTH, -TEXT_HEIGHT)
        glTexCoord2f(t.text_width, t.text_height)
        glVertex2f(TEXT_WIDTH, TEXT_HEIGHT)
        glTexCoord2f(0, t.text_height)
        glVertex2f(-TEXT_WIDTH, TEXT_HEIGHT)

        glEnd()

        
    
class Map(object):
    TILE_SIZE = 32
    @classmethod
    def class_init(cls):
        cls.tiles = {}
        for n in ['grass0', 'rock']:
            cls.tiles[n] = Texture(filename = n + '.png')
            cls.tiles[n].cells_wide = float(cls.tiles[n].surface.get_width() / cls.TILE_SIZE)
            cls.tiles[n].cells_high = float(cls.tiles[n].surface.get_height() / cls.TILE_SIZE)
    @classmethod
    def transform_for(cls, x, y):
        glScalef(*([cls.TILE_SIZE / 2]*3))
        glTranslatef(x*2, y*2, 0)

    def __init__(self, grid):
        self.grid = grid
    def draw(self, x0, y0, x1, y1, frame):
        for y in xrange(y0, y1):
            for x in xrange(x0, x1):
                c = self.grid.get(x, y)
                if c.blocked:
                    t = self.tiles['rock']
                else:
                    t = self.tiles['grass0']
                t.bind()
                glPushMatrix()
                Map.transform_for(x, y)
                glBegin(GL_QUADS)
                # TODO: Se till att molnskuggeberäkningarna inte är fånigt långsamma
                def luminance(x,y):
                    return (math.sin((x + frame*0.08)*0.4) * math.sin((y + frame*0.01)*0.4)) * 0.2 + 0.9
                u0 = x % t.cells_wide
                u1 = u0 + 1
                v0 = y % t.cells_high
                v1 = v0 + 1
                glTexCoord2f(u0 / t.cells_wide, v0 / t.cells_wide)
                glColor3f(*([luminance(x,y)]*3))
                #glVertex2f(self.TILE_SIZE * (x - 0.5), self.TILE_SIZE * (y - 0.5))
                glVertex2f(-1, -1)
                glTexCoord2f(u1 / t.cells_wide, v0 / t.cells_wide)
                glColor3f(*([luminance(x+1,y)]*3))
                #glVertex2f(self.TILE_SIZE * (x + 0.5), self.TILE_SIZE * (y - 0.5))
                glVertex2f(1, -1)
                glTexCoord2f(u1 / t.cells_wide, v1 / t.cells_wide)
                glColor3f(*([luminance(x+1,y+1)]*3))
                #glVertex2f(self.TILE_SIZE * (x + 0.5), self.TILE_SIZE * (y + 0.5))
                glVertex2f(1, 1)
                glTexCoord2f(u0 / t.cells_wide, v1 / t.cells_wide)
                glColor3f(*([luminance(x,y+1)]*3))
                #glVertex2f(self.TILE_SIZE * (x - 0.5), self.TILE_SIZE * (y + 0.5))
                glVertex2f(-1, 1)
                glEnd()
                if c.object:
                    NumberSprite.draw(c.object)
                glPopMatrix()
                    

class RpnView(game.View):
    CLEAR_COLOR = [0.28, 0.24, 0.55, 0.0]
    ROBOT0_COLORS = [[0.6,0.2,0.2,1],[0.6,0.2,0.2,0.7],[0.6,0.2,0.2,0.0]]
    ROBOT1_COLORS = [[0.6,0.6,0.2,1],[0.6,0.6,0.2,0.7],[0.6,0.6,0.2,0.0]]

    def init(self, model):
        self.model = model
        self.robot = RobotSprite(model.robots[0], self.ROBOT0_COLORS[0])
        self.map = Map(model.grid)
        self.center = [0,0]
        self.zoom = DampedValue(random.uniform(0.25, 8), 0.05)
        self.zoom.set_target(2)
        self.center = [DampedValue(random.uniform(-15, 15), 0.05) for n in xrange(2)]
        self.center[0].set_target(0)
        self.center[1].set_target(0)
        self.fade_to_black = DampedValue(1, 0.08)
        self.fade_to_black.set_target(0)

    def update(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(-WIDTH/2, WIDTH/2, HEIGHT/2, -HEIGHT/2)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.zoom.update()
        self.center[0].update()
        self.center[1].update()
        glPushMatrix()
        glScalef(*([self.zoom()]*3))
        glTranslatef(-self.center[0]() * Map.TILE_SIZE,
                     -self.center[1]() * Map.TILE_SIZE,
                     0)

        glClearColor(*self.CLEAR_COLOR)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        x0 = int(-WIDTH / 2 / Map.TILE_SIZE / self.zoom() + self.center[0]()) - 1
        x1 = int(WIDTH / 2 / Map.TILE_SIZE / self.zoom() + self.center[0]()) + 2
        y0 = int(-HEIGHT / 2 / Map.TILE_SIZE / self.zoom() + self.center[1]()) - 1
        y1 = int(HEIGHT / 2 / Map.TILE_SIZE / self.zoom() + self.center[1]()) + 2
        self.map.draw(x0,y0,x1,y1, self.model.frames)
        glPushMatrix()
        x, y = self.model.robots[0].target_x, self.model.robots[0].target_y
        Map.transform_for(x, y)
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUAD_STRIP)
        cell = self.model.grid.get(x, y)
        if cell.has_action():
            alpha = 0.75 + math.sin(self.model.frames * 0.1) * 0.25
            if cell.object:
                if self.model.robots[0].stack_full():
                    glColor4f(1,1,0,alpha)
                else:
                    glColor4f(0,1,0,alpha)
            else:
                if self.model.robots[0].stack_empty():
                    glColor4f(0,0,0,alpha * 0.5)
                else:
                    glColor4f(0,1,1,alpha)
        else:
            alpha = 0.75 + math.sin(self.model.frames) * 0.25
            glColor4f(1,0,0,alpha)
        OUTER = 1
        INNER = 0.8
        glVertex2f(-OUTER, -OUTER)
        glVertex2f(-INNER, -INNER)
        glVertex2f(OUTER, -OUTER)
        glVertex2f(INNER, -INNER)
        glVertex2f(OUTER, OUTER)
        glVertex2f(INNER, INNER)
        glVertex2f(-OUTER, OUTER)
        glVertex2f(-INNER, INNER)
        glVertex2f(-OUTER, -OUTER)
        glVertex2f(-INNER, -INNER)
        glEnd()
        glPopMatrix()
        glEnable(GL_TEXTURE_2D)
        self.robot.draw()

        glPopMatrix()


        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUAD_STRIP)
        glColor4fv(self.ROBOT0_COLORS[0])
        glVertex2f(-WIDTH * 0.5, -HEIGHT * 0.5)
        glVertex2f(-WIDTH * 0.5, HEIGHT * 0.5)
        glColor4fv(self.ROBOT0_COLORS[1])
        glVertex2f(-WIDTH * 0.42, -HEIGHT * 0.5)
        glVertex2f(-WIDTH * 0.42, HEIGHT * 0.5)
        glColor4fv(self.ROBOT0_COLORS[2])
        glVertex2f(-WIDTH * 0.41, -HEIGHT * 0.5)
        glVertex2f(-WIDTH * 0.41, HEIGHT * 0.5)
        glEnd()
        glBegin(GL_QUAD_STRIP)
        glColor4fv(self.ROBOT1_COLORS[0])
        glVertex2f(WIDTH * 0.5, -HEIGHT * 0.5)
        glVertex2f(WIDTH * 0.5, HEIGHT * 0.5)
        glColor4fv(self.ROBOT1_COLORS[1])
        glVertex2f(WIDTH * 0.42, -HEIGHT * 0.5)
        glVertex2f(WIDTH * 0.42, HEIGHT * 0.5)
        glColor4fv(self.ROBOT1_COLORS[2])
        glVertex2f(WIDTH * 0.41, -HEIGHT * 0.5)
        glVertex2f(WIDTH * 0.41, HEIGHT * 0.5)
        glEnd()

        glEnable(GL_TEXTURE_2D)
        glPushMatrix()
        glTranslate(-WIDTH * 0.46, Map.TILE_SIZE * 5 * 2, 0)
        glScale(*([Map.TILE_SIZE]*3))
        for number in self.model.robots[0].stack:
            NumberSprite.draw(number)
            glTranslate(0, -2, 0)
        glPopMatrix()
        #glScale(*([2]*3))

        self.fade_to_black.update()
        if self.fade_to_black() > 0.01:
            glDisable(GL_TEXTURE_2D)
            glBegin(GL_QUADS)
            glColor4f(0,0,0,self.fade_to_black())
            glVertex2f(-WIDTH/2, -HEIGHT/2)
            glVertex2f(WIDTH/2, -HEIGHT/2)
            glVertex2f(WIDTH/2, HEIGHT/2)
            glVertex2f(-WIDTH/2, HEIGHT/2)
            glEnd()

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
game.py.mouse.set_visible(False)

BodyPart.class_init()
Map.class_init()
NumberSprite.class_init()
Texture.class_init()
game.Music.songs['catoblepas'] =  game.Music.Song(files["GibIt-BorderlineTerritoryoftheCatoblepas.ogg"], 666, 4, 0, 0)

model = Model()
view = RpnView(screen, model)
controller = RpnController(view, model)
music = game.Music()
music.play()

controller.event_loop()

music.stop()

game.py.quit()

######################################################################
