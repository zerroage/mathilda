import re
import traceback

# noinspection PyUnresolvedReferences
from fractions import *
# noinspection PyUnresolvedReferences
from math import *
from time import gmtime, strftime

# noinspection PyUnresolvedReferences
import sublime
# noinspection PyUnresolvedReferences
import sublime_plugin
from collections import OrderedDict

# TODO
# Bug: when there is an 'Answer line' after the current line (maybe even for another expression), expression does not update it's own answer
# Automatically update 'VARIABLES' when switching to another Worksheet
# Define functions like f(a, b, c) = : translate internally to lambdas

ANSWER_LINE = "\t\t\tAnswer = "
ANSWER_PATTERN = "^\\s*Answer\\s*=\\s*.*$"
CR_LF = "\n"


def local_vars(view):
    if not hasattr(view, "local_vars"):
        view.local_vars = OrderedDict()

    return view.local_vars


def myfun(x, y, z):
    return x ** 2 + y / z


mylam = lambda x, y: x / y ** 2


def print_answer(view, edit, line, answer):
    if not answer:
        return

    ans_line = view.find(ANSWER_PATTERN, line.end() + 1)
    ans_text = ANSWER_LINE + str(answer)
    if ans_line is not None and 0 < ans_line.begin() <= line.end() + 1:
        view.replace(edit, ans_line, ans_text)
    else:
        view.insert(edit, line.end(), CR_LF + ans_text)


def preprocess_expression(left, right):
    if left:
        m = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)\(([a-zA-Z0-9_,]+)\)", left)
        if m:
            return m.group(1), "lambda " + m.group(2) + " : " + right

    return left, right


def postprocess_answer(var, expr, answer):
    txt = str(answer) if answer else ""
    if "<function <lambda" in txt:
        return expr

    return answer


def calc(view, edit, line):
    line_contents = view.substr(line).lower()
    line_contents = re.sub('\\s+', '', line_contents)

    # print("CALCULATING LINE: " + str(line_contents))

    if len(line_contents) == 0 or line_contents.startswith((';', '#', "'")) or line_contents.startswith('answer'):
        return None

    parts = re.split('=', line_contents)

    right_part = parts[0] if len(parts) == 1 else parts[1]
    left_part = None if (len(parts) == 1) else parts[0]

    right_parts = re.split("[;#']", right_part)
    expr = right_parts[0]

    try:
        (var, expr) = preprocess_expression(left_part, expr)
        answer = eval(expr, globals(), local_vars(view))

        local_vars(view)['ans'] = answer
        if var:
            local_vars(view)[var] = answer

        return postprocess_answer(var, expr, answer)
    except Exception as ex:
        print(traceback.format_exc())
        view.show_popup("<b>Error</b><br>" + str(ex), sublime.HIDE_ON_MOUSE_MOVE_AWAY)
        return None
    finally:
        update_vars(view, edit)


def update_vars(view, edit):
    panel = view.window().find_output_panel("local_vars")

    if panel:
        panel.erase(edit, sublime.Region(0, panel.size()))
        panel.insert(edit, panel.size(), "VARIABLES\n" + "-" * 35 + "\n")
        for k in local_vars(view):
            panel.insert(edit, panel.size(), "{0:16}{1}\n".format(k, local_vars(view)[k]))


class WorksheetRecalculateCommand(sublime_plugin.TextCommand):

    def update_view_name(self, edit):

        # take first line if it is a comment
        line = self.view.line(0)
        line_contents = self.view.substr(line)

        if line_contents.startswith((';', '#', "'")):
            self.view.set_name(line_contents.strip("';# "))

    def run(self, edit, new_line=False):
        self.update_view_name(edit)
        local_vars(self.view).clear()

        point = 0
        limit = 0
        while point < self.view.size() and limit < 10000:
            line = self.view.line(point)
            point = line.end() + 1
            answer = calc(self.view, edit, line)
            print_answer(self.view, edit, line, answer)
            limit += 1

        if new_line:
            for region in self.view.sel():
                line = self.view.line(region)

                ans_line = self.view.find(ANSWER_PATTERN, line.end() + 1)
                eof = False
                if ans_line is not None and 0 < ans_line.begin() <= line.end() + 1:
                    reg = ans_line.end() + 1
                else:
                    reg = line.end() + 1

                if reg > self.view.size():
                    reg = self.view.size()
                    eof = True

                self.view.sel().clear()
                self.view.insert(edit, reg, CR_LF)
                self.view.sel().add(reg + 1 if eof else reg)

        self.view.set_status('worksheet', "Updated worksheet at " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))


class ToggleCommentCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        for region in self.view.sel():
            line = self.view.line(region)
            line_contents = self.view.substr(line)

            self.view.sel().clear()
            self.view.sel().add(line.end() + 1)

            if line_contents.startswith(('#', ';')):
                # uncomment
                self.view.replace(edit, line, re.sub('^[#;]+\\s*', '', line_contents))
            else:
                # comment
                self.view.insert(edit, line.begin(), '# ')


class ListVarsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.view.window().create_output_panel("local_vars")
        self.view.window().run_command('show_panel', {"panel": 'output.local_vars'})
        update_vars(self.view, edit)

        img = '<img src="data:image/gif;base64,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">'
        # self.view.show_popup(img)

        # view.insert(edit, "Some text")
        # self.view.show_popup(line_contents, sublime.HIDE_ON_MOUSE_MOVE_AWAY)

        # self.view.window().show_quick_panel(["Goto Line:", "Item 2"], None)
        # self.window.show_input_panel("Goto Line:", "", self.on_done, None, None)

        # phantom_set = sublime.PhantomSet(self.view)
        # phantom = sublime.Phantom(sublime.Region(0, 20), "<body><p>HELLO<p></body>", sublime.LAYOUT_BELOW)
        # self.view.erase_phantoms("test")
        # self.view.add_phantom("test", sublime.Region(20, 40), "HELLO!<a href='#'>Click me!</a><br>" +
        # img +
        # "<div style='position:absolute'><div style='display:block; border-radius: 5px; border: 1px solid white; padding: 10px'>DIV!</div><br>" +
        # "<div style='width:3; height:3; background-color: #ff0088; position: absolute; top: 100; left: 30'> </span>" +
        # "<div style='width:3; height:3; background-color: #008800; position: absolute; top: 80; left: 30'> </span>" +
        # "</div>", sublime.LAYOUT_BELOW)
        # phantom_set.update([phantom])

    # def on_done(self, text):
    #     try:
    #         line = int(text)
    #         if self.window.active_view():
    #             self.window.active_view().run_command("goto_line", {"line": line})
    #     except ValueError:
    #         pass
