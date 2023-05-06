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


class ContextHolder:
    def __init__(self) -> None:
        self.clear()

    class ResultItem:
        def __init__(self, var_name="", value="", remark="", stack="", section="") -> None:

            self.var_name = var_name
            self.value = value
            self.remark = remark
            self.stack = stack
            self.section = section

    class ResultsHolder:
        def __init__(self, name, remark=""):
            self.name = name
            self.remark = remark
            self.items = []

        def get_item_values_list(self):
            return [r.value for r in self.items]

    def clear(self):
        self.vars_dict = {}
        self.history = []
        self.stacks = []
        self.sections = []

    def get_evaluation_context(self):
        context = {}

        vars_dict = {k: v.value for (k, v) in self.vars_dict.items()}
        stacks_dict = {s.name: s.get_item_values_list() for s in self.stacks}

        context.update(vars_dict)
        context.update(stacks_dict)

        context['__CURRENT_STACK'] = self.stacks[-1].get_item_values_list() if len(self.stacks) > 0 else []
        context['ans'] = self.history[-1].value if len(self.history) > 0 else 0

        return context

    def get_vars(self):
        return self.vars_dict

    def store_result(self, var_name, value, remark=""):
        # TODO: Don't put stacks on stack :-)
        # if not isinstance(value, list):

        stack_name = self.stacks[-1].name if len(self.stacks) > 0 else ""
        section_name = self.sections[-1].name if len(self.sections) > 0 else ""
        result = self.ResultItem(var_name, value, remark, stack_name, section_name)

        if var_name:
            self.vars_dict[var_name] = result

        # Save calculation history in execution order
        self.history.append(result)

        # Add to the currently active stack and section
        if len(self.stacks) > 0:
            self.stacks[-1].items.append(result)
        if len(self.sections) > 0:
            self.sections[-1].items.append(result)

    def start_new_stack(self, stack_name, remark):
        self.stacks.append(self.ResultsHolder(stack_name, remark))

    def start_new_section(self, section_name):
        self.sections.append(self.ResultsHolder(section_name))


class MathildaBaseCommand(sublime_plugin.TextCommand):

    def is_visible(self):
        return "Mathilda" in self.view.settings().get("syntax")

    def context(self):
        if not hasattr(self.view, "context"):
            self.view.context = ContextHolder()
        return self.view.context

    def update_vars(self, edit):

        def build_vars_map(vars):
            vars_map = {}
            for k in vars:
                if not str(k).startswith('__'):
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
            vars_map = build_vars_map(self.context().get_evaluation_context())
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
        self.context().clear()
        self.context().start_new_stack("__stack", 'Anonymous stack')
        self.view.erase_regions("errors")

        error_regions = []
        error_annotations = []
        point = 0
        limit = 0
        while point < self.view.size() and limit < 10000:
            line = self.view.line(point)
            point = line.end() + 1

            expression = self.view.substr(line).lower().strip()
            remark = ""

            if not expression:
                continue

            # Process lines with answers
            if expression.startswith('answer'):
                continue

            # Process basic comments    
            if expression.startswith(';'):
                continue
            
            if expression.startswith('#'):
                section_name = expression.lstrip("#")
                self.context().start_new_section(section_name)
                continue

            # Process comments
            expression_with_remark = re.split("[;#']", expression, 1)
            if len(expression_with_remark) > 1:
                expression = expression_with_remark[0]
                remark = expression_with_remark[1]

            # Process stacks
            if expression.startswith('@'):
                stack_name = expression.lstrip('@').strip()
                # Sanitize stack name
                m = re.match(r'[a-zA-Z][a-zA-Z0-9_]*', stack_name)
                if m:
                    self.context().start_new_stack(stack_name, remark)
                    continue

            # Evaulate line
            try:
                (var_name, answer) = self.evaluate(expression)
                pretty_answer = self.prettify(var_name, expression, answer)

                self.context().store_result(var_name, answer, remark)
                self.print_answer(self.view, edit, line, pretty_answer)
            except Exception as ex:
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

    def evaluate(self, expr):
        expr = self.desugar_expression(expr)
        (var_name, expr) = self.parse_var_or_function_declaration(expr)

        result = eval(expr, globals(), self.context().get_evaluation_context())
        return (var_name, result)

    def print_answer(self, view, edit, line, answer):
        if not answer:
            return

        ans_line = view.find(ANSWER_PATTERN, line.end() + 1)
        ans_text = ANSWER_LINE + str(answer)
        if ans_line is not None and 0 < ans_line.begin() <= line.end() + 1:
            view.replace(edit, ans_line, ans_text)
        else:
            view.insert(edit, line.end(), CR_LF + ans_text)

    def desugar_expression(self, expr):
        # Factorial
        expr = re.sub(r'(\d+)!', r'factorial(\1)', expr)

        # Unicode symbols
        expr = re.sub(r'(?u)\u00f7', '/', expr)
        expr = re.sub(r'(?u)\u00d7', '*', expr)
        expr = re.sub(r'(?u)\u00b2', '**2', expr)
        expr = re.sub(r'(?u)\u00b3', '**3', expr)
        expr = re.sub(r'(?u)\u00b4', '**4', expr)
        expr = re.sub(r'(?u)\u00b5', '**5', expr)
        expr = re.sub(r'(?u)\u00b6', '**6', expr)
        expr = re.sub(r'(?u)\u00b7', '**7', expr)
        expr = re.sub(r'(?u)\u00b8', '**8', expr)
        expr = re.sub(r'(?u)\u00b29', '**9', expr)
        expr = re.sub(r'(?u)\u221a([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/2)', expr)
        expr = re.sub(r'(?u)\u221a\((.+?)\)', r'(\1)**(1/2)', expr)
        expr = re.sub(r'(?u)\u221b([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/3)', expr)
        expr = re.sub(r'(?u)\u221b\((.+?)\)', r'(\1)**(1/3)', expr)
        expr = re.sub(r'(?u)\u221c([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/4)', expr)
        expr = re.sub(r'(?u)\u221c\((.+?)\)', r'(\1)**(1/4)', expr)

        # Percent arithmetic: A */ N% transforms to A */ (N ÷ 100)
        expr = re.sub(r'([*/])\s*([0-9.]+)%', r'\1(\2/100)', expr)

        # Percent arithmetic: A ± N% transforms to A ± A * (N ÷ 100)
        expr = re.sub(r'([+-])\s*([0-9.]+)%', r'*(1\1\2/100)', expr)

        # M:N transforms to Fraction(M, N)
        expr = re.sub(r'(\d+):(\d+)', r'Fraction(\1, \2)', expr)

        # ::N transforms to Fraction(N)
        expr = re.sub(r':::([0-9.]+)', r'Fraction(\1)', expr)
        expr = re.sub(r'::([0-9.]+)', r'Fraction(\1).limit_denominator()', expr)

        # Date arithmetic
        expr = re.sub(r'today', 'date.today()', expr, flags=re.IGNORECASE)
        expr = re.sub(r'now', 'datetime.today()', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*sec(ond(s)?)?', r'timedelta(seconds = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*min(ute(s)?)?', r'timedelta(minutes = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*hour(s)?', r'timedelta(hours = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*day(s)?', r'timedelta(days = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*week(s)?', r'timedelta(weeks = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*month(s)?', r'relativedelta(months = \1)', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\d+)\s*year(s)?', r'relativedelta(years = \1)', expr, flags=re.IGNORECASE)

        # Current stack syntactic sugar
        expr = re.sub(r'@(\d+)', r'(__CURRENT_STACK[-\1] if len(__CURRENT_STACK) > \1 else 0)', expr)
        expr = re.sub('@@', '__CURRENT_STACK', expr)
        expr = re.sub('@', 'ans', expr)

        return expr

    def parse_var_or_function_declaration(self, expr):
        if "=" in expr or ":=" in expr:
            (left, right) = re.split('=|:=', expr, 1)
            if left and right:
                # fun_name(arg1, arg2, ...) = ...
                m = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*((?:[a-zA-Z][a-zA-Z0-9_]*)(?:\s*,\s*[a-zA-Z][a-zA-Z0-9_]*)*)\s*\)", left)
                if m:
                    # Make a lambda-function
                    return m.group(1).strop(), ("lambda " + m.group(2) + " : " + right.strip())
                # var_name = ...
                elif re.match(r"[a-zA-Z][a-zA-Z0-9_]*", left):
                    return left.strip(), right.strip()

            raise Exception("Invalid function or variable declaration: <i>%s</i>" % expr)
        else:
            return None, expr.strip()

    def prettify(self, var_name, expr, answer):
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
