import random
import re
import string
import traceback
from collections import OrderedDict
# noinspection PyUnresolvedReferences
from fractions import *
# noinspection PyUnresolvedReferences
from math import *
from time import gmtime, strftime

# noinspection PyUnresolvedReferences
import sublime
# noinspection PyUnresolvedReferences
import sublime_plugin

ANSWER_LINE = "\t\t\tAnswer = "
ANSWER_PATTERN = "^\\s*Answer\\s*=\\s*.*$"
CR_LF = "\n"


def local_vars(view):
    if not hasattr(view, "local_vars"):
        view.local_vars = OrderedDict()

    return view.local_vars


# From https://stackoverflow.com/a/2257449
def password(n):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(n))


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

    # Extract custom function definition
    parts = re.split('=', line_contents)

    right_part = parts[0] if len(parts) == 1 else parts[1]
    left_part = None if (len(parts) == 1) else parts[0]

    # Remove end-of-line comment
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
                self.view.insert(edit, line.begin(), '; ')


class ListVarsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        self.view.window().create_output_panel("local_vars")
        self.view.window().run_command('show_panel', {"panel": 'output.local_vars'})
        update_vars(self.view, edit)
