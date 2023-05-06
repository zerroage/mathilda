import itertools
import random
import re
import string
import traceback
from collections import OrderedDict
from datetime import date, datetime, timedelta
from fractions import Fraction
from functools import reduce
from math import *
from time import gmtime, strftime

import sublime
import sublime_plugin
from dateutil.relativedelta import relativedelta

ANSWER_LINE = "\t\t\tAnswer = "
ANSWER_PATTERN = "^\\s*Answer\\s*=\\s*.*$"
CR_LF = "\n"


# Useful math functions


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


def median(numbers):
    n = len(numbers)
    s = sorted(numbers)
    return (sum(s[n // 2 - 1:n // 2 + 1]) / 2.0, s[n // 2])[n % 2] if n else None


def prod(iterable):
    import operator
    return reduce(operator.mul, iterable, 1)


# Password generation functions


# From https://stackoverflow.com/a/2257449
def password(n):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(n))


# From https://stackoverflow.com/a/5502875
def gibberish(wordcount):
    initial_consonants = (set(string.ascii_lowercase) - set('aeiou')
                          # remove those easily confused with others
                          - set('qxc')
                          # add some crunchy clusters
                          | {'bl', 'br', 'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gr', 'pl', 'pr', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'str',
                             'sw', 'tr'}
                          )

    final_consonants = (set(string.ascii_lowercase) - set('aeiou')
                        # confusable
                        - set('qxcsj')
                        # crunchy clusters
                        | {'ct', 'ft', 'mp', 'nd', 'ng', 'nk', 'nt', 'pt', 'sk', 'sp', 'ss', 'st', 'oy', 'ji', 'ch', 'ee', 'zz', 'fj', 'tz'}
                        )

    # oy, ji, ch, ee, zz, fj, and tz

    vowels = 'aeiou'  # we'll keep this simple

    # each syllable is consonant-vowel-consonant "pronounceable"
    syllables = map(''.join, itertools.product(initial_consonants, vowels, final_consonants))

    # you could trow in number combinations, maybe capitalized versions...
    return ' '.join(random.sample(list(syllables), wordcount))


class MathildaBaseCommand(sublime_plugin.TextCommand):

    INTERNAL_VAR_PREFIX = "__"
    STACK_NAME_INTERNAL_VAR = INTERNAL_VAR_PREFIX + 'stack_name'
    SECTION_NAME_INTERNAL_VAR = INTERNAL_VAR_PREFIX + 'section_name'

    def is_visible(self):
        return "Mathilda" in self.view.settings().get("syntax")
    
    def local_vars(self):
        if not hasattr(self.view, "local_vars"):
            self.view.local_vars = OrderedDict()

        return self.view.local_vars

    def set_local_var(self, var, value):
        if var:
            self.local_vars()[var.lower().strip()] = value

        self.local_vars()['ans'] = value
        self.push_to_current_stack(var, value)

    def get_local_var(self, var):
        return self.local_vars()[var.lower().strip()]

    def clear_local_vars(self):
        self.local_vars().clear()

    def start_new_stack(self, stack_name):
        self.local_vars()[self.STACK_NAME_INTERNAL_VAR] = stack_name
        self.local_vars()[stack_name] = []

    def start_new_section(self, section_name):
        self.local_vars()[self.SECTION_NAME_INTERNAL_VAR] = section_name
        self.local_vars()[section_name] = []

    def push_to_current_stack(self, var, value):
        # Don't put stacks on stack :-)
        if not isinstance(value, list):
            stack_name = self.local_vars()[self.STACK_NAME_INTERNAL_VAR]
            if stack_name:
                if stack_name in self.local_vars():
                    self.local_vars()[stack_name].insert(0, value)

    def update_vars(self, edit):

        def build_vars_map(vars):
            vars_map = {}
            for k in vars:
                if not str(k).startswith(self.INTERNAL_VAR_PREFIX):
                    if isinstance(vars[k], list):
                        vars_map["@" + k] = "<Stack of %d item(s)>" % len(vars[k])
                    else:
                        vars_map[k] = vars[k]
            max_var_name_len = max(list(map(lambda x: len(str(x)), vars_map.keys())))
            max_var_value_len = max(list(map(lambda x: len(str(x)), vars_map.values())))

            table = "VARIABLES\n" + "-" * (max_var_name_len + max_var_value_len + 3) + "\n"
            for k, v in vars_map.items():
                table += "" + str(k).ljust(max_var_name_len) + " : " + str(v).ljust(max_var_value_len) + "\n"

            return table

        panel = self.view.window().find_output_panel("local_vars")

        if panel:
            vars_map = build_vars_map(self.local_vars())
            panel.erase(edit, sublime.Region(0, panel.size()))
            panel.assign_syntax("Mathilda-vars-panel.sublime-syntax")
            panel.insert(edit, panel.size(), str(vars_map))


class RecalculateWorksheetCommand(MathildaBaseCommand):

    def update_view_name(self, edit):

        # take first line if it is a comment
        line = self.view.line(0)
        line_contents = self.view.substr(line)

        if line_contents.startswith((';', '#', "'")):
            self.view.set_name(line_contents.strip("';# "))

    def run(self, edit, new_line=False):
        self.update_view_name(edit)
        self.clear_local_vars()
        self.start_new_stack("__stack")
        self.view.erase_regions("errors")
        
        error_regions = []
        error_annotations = []

        point = 0
        limit = 0
        while point < self.view.size() and limit < 10000:
            line = self.view.line(point)
            point = line.end() + 1

            line_contents = self.view.substr(line).lower().strip()

            if len(line_contents) == 0:
                continue

            if line_contents.startswith('answer'):
                continue

            if line_contents.startswith(';'):
                continue

            if line_contents.startswith('#'):
                section_name = line_contents.lstrip("#")
                self.start_new_section(section_name)
                continue

            if line_contents.startswith('@'):
                stack_name = line_contents.lstrip("@")
                # Sanitize stack name
                stack_name = re.sub(r'[^a-zA-Z0-9]+', '_', stack_name).strip("_")
                # Stack name cannot start with a digit
                stack_name = re.sub(r'^\d+(.*)', r'\1', stack_name)
                if len(stack_name) == 0:
                    stack_name = "stack_%d" % self.view.rowcol(point)[0]
                self.view.replace(edit, line, "@" + stack_name)
                self.start_new_stack(stack_name)
                continue

            try:
                answer = self.calc(self.view, edit, line_contents)
                self.print_answer(self.view, edit, line, answer)
            except Exception as ex:
                # view.show_popup("<b>Error</b><br>" + str(ex), sublime.HIDE_ON_MOUSE_MOVE_AWAY)
                self.print_answer(self.view, edit, line, "ERROR")
                error_regions += [line]
                error_annotations += [str(ex)]
            finally:
                limit += 1
            
        if error_regions:
            self.view.add_regions("errors", error_regions, 
                                  "region.redish", "dot", 
                                  sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL | sublime.DRAW_SQUIGGLY_UNDERLINE, 
                                  error_annotations)
            
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
                
        self.update_vars(edit)
        self.view.set_status('worksheet', "Updated worksheet at " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))

    def calc(self, view, edit, line_contents):

        # Extract custom function definition
        parts = re.split('=', line_contents)

        right_part = parts[0] if len(parts) == 1 else parts[1]
        left_part = None if (len(parts) == 1) else parts[0]

        # Remove end-of-line comment
        right_parts = re.split("[;#']", right_part)
        expr = right_parts[0]

        (var, expr) = self.preprocess_expression(left_part, expr, view)
        answer = eval(expr, globals(), self.local_vars())

        self.set_local_var(var, answer)

        return self.postprocess_answer(var, expr, answer)

    def print_answer(self, view, edit, line, answer):
        if not answer:
            return

        ans_line = view.find(ANSWER_PATTERN, line.end() + 1)
        ans_text = ANSWER_LINE + str(answer)
        if ans_line is not None and 0 < ans_line.begin() <= line.end() + 1:
            view.replace(edit, ans_line, ans_text)
        else:
            view.insert(edit, line.end(), CR_LF + ans_text)

    def preprocess_expression(self, left, right, view):
        if right:
            # Unicode symbols
            right = re.sub(r'(?u)\u00f7', '/', right)
            right = re.sub(r'(?u)\u00d7', '*', right)
            right = re.sub(r'(?u)\u00b2', '**2', right)
            right = re.sub(r'(?u)\u00b3', '**3', right)
            right = re.sub(r'(?u)\u00b4', '**4', right)
            right = re.sub(r'(?u)\u00b5', '**5', right)
            right = re.sub(r'(?u)\u00b6', '**6', right)
            right = re.sub(r'(?u)\u00b7', '**7', right)
            right = re.sub(r'(?u)\u00b8', '**8', right)
            right = re.sub(r'(?u)\u00b29', '**9', right)
            right = re.sub(r'(?u)\u221a([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/2)', right)
            right = re.sub(r'(?u)\u221a\((.+?)\)', r'(\1)**(1/2)', right)
            right = re.sub(r'(?u)\u221b([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/3)', right)
            right = re.sub(r'(?u)\u221b\((.+?)\)', r'(\1)**(1/3)', right)
            right = re.sub(r'(?u)\u221c([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/4)', right)
            right = re.sub(r'(?u)\u221c\((.+?)\)', r'(\1)**(1/4)', right)

            # Percent arithmetic: A */ N% transforms to A */ (N ÷ 100)
            right = re.sub(r'([*/])\s*([0-9.]+)%', r'\1(\2/100)', right)

            # Percent arithmetic: A ± N% transforms to A ± A * (N ÷ 100)
            right = re.sub(r'([+-])\s*([0-9.]+)%', r'*(1\1\2/100)', right)

            # M:N transforms to Fraction(M, N)
            right = re.sub(r'(\d+):(\d+)', r'Fraction(\1, \2)', right)

            # ::N transforms to Fraction(N)
            right = re.sub(r':::([0-9.]+)', r'Fraction(\1)', right)
            right = re.sub(r'::([0-9.]+)', r'Fraction(\1).limit_denominator()', right)

            # Date arithmetic
            right = re.sub(r'today', 'date.today()', right, flags=re.IGNORECASE)
            right = re.sub(r'now', 'datetime.today()', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*sec(ond(s)?)?', r'timedelta(seconds = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*min(ute(s)?)?', r'timedelta(minutes = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*hour(s)?', r'timedelta(hours = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*day(s)?', r'timedelta(days = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*week(s)?', r'timedelta(weeks = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*month(s)?', r'relativedelta(months = \1)', right, flags=re.IGNORECASE)
            right = re.sub(r'(\d+)\s*year(s)?', r'relativedelta(years = \1)', right, flags=re.IGNORECASE)

            # answers stack
            stack_name = self.get_local_var(STACK_NAME_INTERNAL_VAR)
            right = re.sub(r'@(\d+)', r'({0}[\1] if len({0}) > \1 else 0)'.format(stack_name), right)
            right = re.sub('@@', stack_name, right)
            right = re.sub('@', 'ans', right)

        if left:
            m = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)\(([a-zA-Z0-9_,]+)\)", left)
            if m:
                return m.group(1), "lambda " + m.group(2) + " : " + right

        return left, right

    def postprocess_answer(self, var, expr, answer):
        txt = str(answer) if answer is not None else ""
        if "<function <lambda" in txt:
            return expr

        answer = re.sub(', 0:00:00', '', txt)

        return answer


class ToggleCommentCommand(MathildaBaseCommand):

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


class ListVarsCommand(MathildaBaseCommand):

    def run(self, edit):
        self.view.window().create_output_panel("local_vars")
        self.view.window().run_command('show_panel', {"panel": 'output.local_vars'})
        self.update_vars(edit)
