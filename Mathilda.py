import itertools
import random
import re
import string
import inspect
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
from .natu.natu import units as u
from .natu.natu import math as m

ANSWER_LINE = "\t\t\tAnswer = "
FUNCTION_LINE = "\t\t\tFunction: "
ANSWER_PATTERN = "^\\s*(?:Answer\\s*=|Function:)\\s*.*$\n?"
CR_LF = "\n"

# NATU

NATU_UNIT_NAMES = [u for u in u._units]
NATU_BASE_REGEX = "|".join(NATU_UNIT_NAMES)

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

# Generates a bar chart in a table
#
# value:        value in a table row
# group_values: list of values in the tables' group (a stack, or a list)
# all_values:   list of all values in the table
# size:         table colulmn size, limits max bar size
# base_value:   base value for percent calculation, by default percentage is calculated from the maximum absolute value of all rows
# mid_value:    middle line value to generate two-directional bar chart
# mid_char:     symbol to draw the middle line
# left_char:    symbol to draw the left part of the bar chart with values less than mid_value
# right_char:   symbol to draw the right part of the bar chart with values greater than mid_value
# left_tip:     symbol to draw the tip of the left-side bar
# right_tip:    symbol to draw the tip of the right-side bar
# left_fmt:     Python format string to display value or percentage next to the left-side bar
# right_fmt:    Python format string to display value or percentage next to the right-side bar
def bar(value = 0, group_values = [], all_values=[], 
        size = 32, base_value = float('nan'), mid_value = 0, 
        mid_char = "|", left_char="■", right_char="■", left_tip="", right_tip="",
        left_fmt="{percent:.2%} ", right_fmt=" {percent:.2%}"):

    if isnan(base_value):
        base_value = max([abs(v) for v in group_values])

    if base_value == 0:
        return ""
    
    left_char = " " if left_char == "" else left_char[0]
    right_char = " " if right_char == "" else right_char[0]

    min_value = min(group_values)
    max_value = max(group_values)
    if min_value < mid_value < max_value: 
        max_value_range = (max_value - mid_value) + (mid_value - min_value)
    elif min_value < max_value < mid_value:
        max_value_range = mid_value - min_value
    elif mid_value < min_value < max_value:
        max_value_range = max_value - mid_value
    else:
        max_value_range = 0
    
    max_left_txt_len = max([len(left_fmt.format(percent=v/base_value, value=v)) for v in group_values if v <= mid_value] or [0])
    max_right_txt_len = max([len(right_fmt.format(percent=v/base_value, value=v)) for v in group_values if v >= mid_value] or [0])

    left_text = left_fmt.format(percent=value/base_value, value=value)
    right_text = right_fmt.format(percent=value/base_value, value=value)
    
    if min_value <= max_value < mid_value or mid_value > min_value >= max_value:
        mid_char = "" # Don't show middle for bars with one-direction only bars
    
    max_bar_size = size - len(mid_char) - (max_left_txt_len + max_right_txt_len)
    scale = max_bar_size / max_value_range

    bar_size = round(abs(mid_value - value) * scale)
    left_bar_size = bar_size - len(left_tip)
    right_bar_size = bar_size - len(right_tip)

    left_size = round((abs(mid_value - min_value)) * scale)
    full_left_space_size = left_size + max_left_txt_len
    left_space_size = (left_size - bar_size + (max_left_txt_len - len(left_text))) 

    if min_value < mid_value < max_value:
        if value < mid_value:
            bar = left_tip + (left_char * left_bar_size)
            return " " * left_space_size + left_text + bar + mid_char
        else:
            bar = right_char * right_bar_size + right_tip
            return " " * full_left_space_size + mid_char + bar + right_text
    else:
        if min_value <= max_value < mid_value:
            bar = left_tip + (left_char * left_bar_size)
            return " " * left_space_size + left_text + bar
        else:        
            bar = right_char * right_bar_size + right_tip
            return bar + right_text

class TableFormatter:

    def __init__(self, headers) -> None:
        self.headers = headers
        self.current_row_group = ""
        self.row_groups = OrderedDict()
        self.subtotal_groups = OrderedDict()
        self.totals = []
        self.start_row_group()

    def add_row(self, row):
        self.row_groups[self.current_row_group].append(row)

    def add_subtotal(self, total):
        self.subtotal_groups[self.current_row_group].append(total)
        
    def add_total(self, total):
        self.totals.append(total)
        
    def start_row_group(self, group_name = ""):
        self.current_row_group = group_name
        if not group_name in self.row_groups:
            self.row_groups[group_name] = []
            self.subtotal_groups[group_name] = []

    def format_table(self):
        # Flatten list of lists (returned by dict.values() method)
        all_rows = [self.headers] + \
            list(itertools.chain(*self.row_groups.values())) + \
            list(itertools.chain(*self.subtotal_groups.values())) + \
            self.totals
        
        columns = max([len(r) for r in all_rows])
        column_widths = [max([len(str(r[c])) for r in all_rows if len(r) > c]) for c in range(columns)]

        top_div = "|-" + "---".join(['-' * w for w in column_widths]) + "-|\n"
        divider = "|-" + "-|-".join(['-' * w for w in column_widths]) + "-|\n"
        row_fmt = "| " + " | ".join(['{:%s}' % w for w in column_widths]) + " |\n"
        sub_fmt = "| " + "{:%s}" % (sum(column_widths) + 3 * (columns - 1)) + " |\n" # two spaces and col.separator between colulmns
        mid_div = "|-" + "---".join(['-' * w for w in column_widths]) + "-|\n"   # Ending new line will be inserted separately
        bot_div = "|-" + "---".join(['-' * w for w in column_widths]) + "-|"   # Ending new line will be inserted separately

        r = []
        for k, v in self.row_groups.items():
            if len(v) > 0:
                # Do not add middle divider at the first position
                if len(r) > 0:
                    r += [mid_div]
                if len(k.strip()) > 0:
                    r += [self.format_row(sub_fmt, [k], 1)]
                    r += [mid_div]
                r += [self.format_row(row_fmt, r, columns) for r in v]
                if len(self.subtotal_groups[k]) > 0:
                    r += [mid_div]
                    r += [self.format_row(row_fmt, r, columns) for r in self.subtotal_groups[k]]

        if len(self.totals) > 0:
            r += [mid_div]
            r += [self.format_row(row_fmt, r, columns) for r in self.totals]
            

        # Reminder for myself: '*' unpacks a list to function arguments
        return "".join([top_div] + 
                       [self.format_row(row_fmt, self.headers, columns)] +
                       [divider if len(self.row_groups) == 1 or len(self.row_groups[""]) > 0 else mid_div] +
                       r +
                       [bot_div])

    def format_row(self, format_str, row, num_of_columns):
        # Add missing columns to rows
        fmt_params = row + [''] * (num_of_columns - len(row))
        return format_str.format(*fmt_params)

class ContextHolder:
    def __init__(self) -> None:
        self.clear()

    class ResultItem:
        def __init__(self, var_name="", value="", remark="", fmt="", stack="", section="") -> None:

            self.var_name = var_name.strip() if var_name else None
            self.value = value
            self.remark = remark.strip()
            self.fmt = fmt.strip()
            self.stack = stack.strip()
            self.section = section.strip()

    class ResultsHolder:
        def __init__(self, name, remark="", fmt=""):
            self.name = name.strip()
            self.remark = remark.strip()
            self.fmt = fmt.strip()
            self.items = []

        def get_item_values_list(self):
            return [r.value for r in self.items]

    def clear(self):
        self.vars_dict = {}
        self.history = []
        self.stacks = []
        self.sections = []

    def get_evaluation_context(self):
        context = globals()

        vars_dict = {k: v.value for (k, v) in self.vars_dict.items()}
        stacks_dict = {s.name: s.get_item_values_list() for s in self.stacks}

        context.update(vars_dict)
        context.update(stacks_dict)

        context['__CURRENT_STACK'] = self.stacks[-1].get_item_values_list() if len(self.stacks) > 0 else []
        ans = self.history[-1].value if len(self.history) > 0 else 0
        context['ans'] = ans
        context['Ans'] = ans
        context['ANS'] = ans
        return context

    def get_vars(self):
        return self.vars_dict
    
    def has_stack(self, stack_name):
        return stack_name in [s.name for s in self.stacks]
    
    def get_stack(self, stack_name):
        return next(s for s in self.stacks if s.name == stack_name)
    
    def get_stack_vars(self, stack_name):
        return [v for v in self.history if v.stack == stack_name]

    def store_result(self, var_name, value, remark="", fmt="", push_to_stack=True):
        # TODO: Don't put stacks on stack :-)
        # if not isinstance(value, list):

        stack_name = self.stacks[-1].name if len(self.stacks) > 0 else ""
        section_name = self.sections[-1].name if len(self.sections) > 0 else ""
        # Use stack formatting settings by default if not specified for the expression
        stack_fmt = self.get_stack(stack_name).fmt
        fmt = fmt or stack_fmt
        result = self.ResultItem(var_name, value, remark, fmt, stack_name, section_name)

        if var_name:
            self.vars_dict[var_name.strip()] = result

        if not callable(result.value):
            # Save calculation history in execution order
            if push_to_stack:
                self.history.append(result)

            # Add to the currently active stack and section
            if len(self.stacks) > 0 and push_to_stack:
                self.stacks[-1].items.append(result)
            if len(self.sections) > 0 and push_to_stack:
                self.sections[-1].items.append(result)
        
        return result

    def start_new_stack(self, stack_name, remark, fmt=""):
        self.stacks.append(self.ResultsHolder(stack_name, remark, fmt))

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

    # 'Enter' key behaviour when pressed inside an expression (non only in the end of a line):
    # False just inserts a new line
    # True behaves like if 'Enter' key was pressed in the end of line: evaluate line and print answer
    EVAL_ON_PRESSING_ENTER_INSIDE_EXPRESSION = True

    # When set to 'True', anonymous values (without named variables) from stacks are shown in a table,
    # otherwise only stack variables are shown. 
    SHOW_UNASSIGNED_VALUES_IN_TABLE = True

    # When set to 'True', any recognized units from the 'natu' module will be used. 
    # For example 'kg' will be replaced with the corresponding NATU unit. When set to 'False' all
    # words will be treated just like normal variables or functions
    USE_NATU = True

    # When set to 'True', the NATU units are prettified: powers are shown with Unicode symbols, 
    # multiplication sign is changed to the Unicode multiplication dot.
    PRETTIFY_NATU_RESULT = True

    # When set to t'True', exponential (e-10) results are formatted in the nice form using Unicode characters
    # for power notation, e.g. '1e5' is shown as '1⋅10⁵'. When set to 'False', the exponent notation is printed as is
    PRETTIFY_EXPONENT = True
    
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

        # Move the carret only when 'Enter' key was pressed
        if new_line:
            self.pre_move_carret(edit)

        while point < self.view.size() and limit < 10000:
            line = self.view.line(point)
            point = self.view.full_line(point).end()
            expression = self.view.substr(line).strip()
            remark = ""
            fmt = ""
            push_to_stack = True

            if not expression:
                continue

            # Process lines with answers
            if expression.lower().startswith('answer'):
                continue

            # Process basic comments
            if expression.startswith(';'):
                continue

            # Process section (header comments)
            if expression.startswith('#'):
                section_name = expression.lstrip("#")
                self.context().start_new_section(section_name)
                continue

            # Process remarks
            expression_with_remark = re.split("[;#']", expression, 1)
            if len(expression_with_remark) > 1 and not expression.startswith('!'):
                expression = expression_with_remark[0].strip()
                remark = expression_with_remark[1].strip()

                # Process formatting rules
                remark, fmt = self.get_formatting(remark)

            # Process stacks
            if expression.startswith('@'):
                stack_name = expression.lstrip('@').strip()
                # Sanitize stack name
                m = re.match(r'[a-zA-Z][a-zA-Z0-9_]*', stack_name)
                if m:
                    self.context().start_new_stack(stack_name, remark, fmt)
                    continue

            # Process "don't push to stack" directive: ?
            if expression.startswith('?'):
                expression = expression.lstrip('?').strip()
                push_to_stack = False

            # Ignore generated tables
            if expression.startswith('|'):
                continue

            if expression.startswith('!SET '):
                self.set_parameter(expression.lstrip('!SET'))
                continue

            chars_inserted = 0
            try:
                if expression.startswith('!'):
                    # Generate a report table
                    chars_inserted = self.generate_table(self.view, edit, line, expression.lstrip('!'))
                else:
                    # Evaulate expression
                    (var_name, answer) = self.evaluate(expression)                    

                    result = self.context().store_result(var_name, answer, remark, fmt, push_to_stack)
                    pretty_answer = self.format_and_prettify(expression, result.value, result.fmt)                    
                    chars_inserted = self.print_answer(self.view, edit, line, answer, pretty_answer)

            except Exception as ex:
                traceback.print_exc() 
                error_regions += [line]
                error_annotations += [str(ex)]
            finally:
                point = line.end() + chars_inserted + 1
                limit += 1

        if error_regions:
            self.view.add_regions("errors", error_regions,
                                  "region.redish", "dot",
                                  sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL | sublime.DRAW_SQUIGGLY_UNDERLINE,
                                  error_annotations)

        # Move the carret only when 'Enter' key was pressed
        if new_line:
            self.move_carret(edit)

        self.update_vars(edit)
        self.view.set_status('worksheet', "Updated on " + strftime("%Y-%m-%d at %H:%M:%S", gmtime()))

    def get_formatting(self, remark, fmt = ""):
        m = re.search(r"\{\S*\}", remark)
        if m:
            fmt = m.group(0)
            remark = remark[:m.start(0)] + remark[m.end(0):]
        return remark.strip(), fmt.strip()

    def pre_move_carret(self, edit):
        # At this moment expressions are not evaluated yet
        # Depending on the configuration we either insert a new line, or move the carret to the end of line
        
        for (i,s) in enumerate(self.view.sel()):
            if self.EVAL_ON_PRESSING_ENTER_INSIDE_EXPRESSION:
                line = self.view.line(s)
                del self.view.sel()[i]
                self.view.sel().add(line.end())

    def move_carret(self, edit):
        # At this moment all carrets are at the last character(s) of answer line(s)
        # Add an empty line or move carret to the next empty line if exists
        
        for s in self.view.sel():
            pos = s.end() + 1
            line = self.view.line(pos)
            if line.empty() or len(self.view.substr(line).strip()) == 0:
                self.view.erase(edit, self.view.full_line(pos))
            self.view.insert(edit, s.end(), CR_LF)


    def evaluate(self, expr):        
        (var_name, expr) = self.parse_var_or_function_declaration(expr)
        expr = self.desugar_expression(expr)
        context = self.context().get_evaluation_context()
        result = eval(expr, context, context)
        return (var_name, result)

    def print_answer(self, view, edit, line, answer, pretty_answer):
        if not answer:
            return 0
        prev_answer_pos = line.end() + 1  # Take into account the new line character
        prev_answer_line = view.find(ANSWER_PATTERN, prev_answer_pos)
        # Erase previous answer if it exists
        if prev_answer_line is not None and 0 < prev_answer_line.begin() <= prev_answer_pos:
            view.erase(edit, prev_answer_line)
        answer_text = CR_LF + (FUNCTION_LINE if callable(answer) else ANSWER_LINE) + str(pretty_answer)
        return view.insert(edit, line.end(), answer_text)

    def desugar_expression(self, expr):
        # Factorial
        expr = re.sub(r'([0-9a-zA-Z_]+)!', r'factorial(\1)', expr)

        # Unicode symbols
        expr = re.sub(r'(?u)\u00f7', '/', expr)
        expr = re.sub(r'(?u)\u00d7', '*', expr) # ×
        expr = re.sub(r'(?u)\u22c5', '*', expr) # ⋅
        expr = re.sub(r'(?u)\u00b2', '**2', expr)
        expr = re.sub(r'(?u)\u00b3', '**3', expr)
        expr = re.sub(r'(?u)\u2074', '**4', expr)
        expr = re.sub(r'(?u)\u2075', '**5', expr)
        expr = re.sub(r'(?u)\u2076', '**6', expr)
        expr = re.sub(r'(?u)\u2077', '**7', expr)
        expr = re.sub(r'(?u)\u2078', '**8', expr)
        expr = re.sub(r'(?u)\u2079', '**9', expr)
        expr = re.sub(r'(?u)\u221a([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/2)', expr) # √
        expr = re.sub(r'(?u)\u221a\((.+?)\)', r'(\1)**(1/2)', expr)
        expr = re.sub(r'(?u)\u221b([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/3)', expr) # ∛
        expr = re.sub(r'(?u)\u221b\((.+?)\)', r'(\1)**(1/3)', expr)
        expr = re.sub(r'(?u)\u221c([0-9.a-zA-Z_]+?\b)', r'(\1)**(1/4)', expr) # ∜
        expr = re.sub(r'(?u)\u221c\((.+?)\)', r'(\1)**(1/4)', expr)

        # Percent arithmetic: A */ N% transforms to A */ (N ÷ 100)
        expr = re.sub(r'([*/])\s*([0-9.a-zA-Z_]+)%', r'\1(\2/100)', expr)

        # Percent arithmetic: A ± N% transforms to A ± A * (N ÷ 100)
        expr = re.sub(r'([+-])\s*([0-9.a-zA-Z_]+)%', r'*(1\1\2/100)', expr)

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

        # NATU
        if self.USE_NATU and not expr.startswith("lambda "):
            rex = r"(?:\b)(" + NATU_BASE_REGEX + r")(?:\b)"
            expr = re.sub(rex, r"u._units['\1']", expr) 

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
                m = re.match(r"^([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*((?:[a-zA-Z][a-zA-Z0-9_]*)(?:\s*,\s*[a-zA-Z][a-zA-Z0-9_]*)*)\s*\)", left)
                if m:
                    # Make a lambda-function
                    return m.group(1).strip(), ("lambda " + m.group(2) + " : " + right.strip())
                # var_name = ...
                elif re.match(r"^[a-zA-Z][a-zA-Z0-9_]*", left):
                    return left.strip(), right.strip()

            raise Exception("Invalid function or variable declaration: <i>%s</i>" % expr)
        else:
            return None, expr.strip()

    def format_and_prettify(self, expr, answer, fmt=""):
        from .natu.natu import core as core
        from .natu.natu import util as util
        
        txt = ""
        unit_txt = ""
        
        if isinstance(answer, core.Quantity):
            display_unit = core.display_unit(answer)
            unit = core.unitspace(**display_unit)
            value = answer / unit
            if fmt:
                txt = fmt.format(value)
            else:    
                txt = str(value)
            # dim = core.dimension(answer)
            unit_txt = str(unit)

            if self.PRETTIFY_NATU_RESULT:
                unit_txt = format(unit, 'U').replace(' ', '⋅')
            
        elif answer is not None:
            if type(answer) == list or type(answer) == tuple:
                txt = str(answer)
            elif fmt and not callable(answer):
                txt = fmt.format(answer)
            else:    
                txt = str(answer)
        
        if self.PRETTIFY_EXPONENT:
            txt = util.format_e(txt, 'U').replace('✕', '⋅')
        
        if "<function <lambda" in txt:
            return expr

        # Fix datetime display
        txt = re.sub(', 0:00:00', '', txt)
        txt = re.sub(r'(\d\d:\d\d:\d\d)\.\d+$', r'\1', txt)
        
        return txt + " " + unit_txt

    def set_parameter(self, expr):
        kv = re.split('[\=\:]', expr)
        if len(kv) > 1:
            param = kv[0].strip().upper()
            value = kv[1].strip().upper()
            bool_value = True if value == 'YES' or value == 'TRUE' or value == 'ON' else False
            
            if param == 'NATU':
                self.USE_NATU = bool_value
            elif param == 'NATU-PRETTY':
                self.PRETTIFY_NATU_RESULT = bool_value
            elif param == 'PRETTY-EXP':
                self.PRETTIFY_EXPONENT = bool_value
            elif param == 'SHOW-UNASSIGNED-VALUES-IN-TABLE':
                self.SHOW_UNASSIGNED_VALUES_IN_TABLE = bool_value
        
    def generate_table(self, view, edit, line, expr):
        
        def invoke_table_fun(fn, args):
            fn_args = args[:fn['numargs']]
            result = fn['func'].__call__(*fn_args)
            return self.format_and_prettify("", result, fn['fmt'])

        if not expr:
            return 0

        vars_list = re.split('[,;]', expr)
        
        extra_col_funcs = []
        sub_total_funcs = []
        total_funcs = []
        for idx, item in enumerate(vars_list):
            var_name = item.replace("{:", "{$") # mask formatting colon to avoid splitting the string in the wrong place
            var_parts = re.split(':', var_name.strip())
            if len(var_parts) > 1:
                func_type = var_parts[0].strip()
                func_name = var_parts[1].strip()
                func_title = func_name
                fmt = ""
                func = None
                
                if func_name in self.context().get_vars():                    
                    f = self.context().get_vars()[func_name]
                    func = f.value
                    fmt = f.fmt
                    func_title = f.remark
                elif func_name in globals():
                    func = globals().get(func_name)
                    func_title = func_name
                elif func_name in globals()['__builtins__']:
                    func = globals()['__builtins__'].get(func_name)
                    func_title = func_name

                if len(var_parts) > 2:                    
                    title = var_parts[2].strip('"\'')
                    title = title.replace("{$", "{:") # unmask colon and extract formatting if any
                    title, fmt = self.get_formatting(title, fmt)
                    func_title = title or func_title
                
                if callable(func):
                    del vars_list[idx]
                    numargs = 1 if inspect.isbuiltin(func) else len(inspect.getfullargspec(func).args)
                    
                    func_desc = {"type": func_type, "name": func_name, "title": func_title, "func": func, "fmt": fmt, "numargs": numargs}
                    if func_type == "c" or func_type == "col" or func_type == "column":
                        extra_col_funcs += [func_desc]
                    elif func_type == "s" or func_type == "sub" or func_type == "subtotal":
                        sub_total_funcs += [func_desc]
                    elif func_type == "t" or func_type == "total":
                        total_funcs += [func_desc]

        # Collect all table values to be passed to aggregate functions
        all_table_data = []
        non_stack_table_data = []
        for var_name in vars_list:
            var_name = var_name.strip()
            if var_name in self.context().get_vars():
                v = self.context().get_vars()[var_name]
                if type(v.value) == list:
                    all_table_data += [(w[1] if type(w) == tuple else w) for w in v.value]
                else:
                    all_table_data += [v.value]
                    non_stack_table_data += [v.value]
            elif self.context().has_stack(var_name):
                stack_vars = self.context().get_stack_vars(var_name)
                for v in stack_vars:
                    if v.var_name or self.SHOW_UNASSIGNED_VALUES_IN_TABLE:
                        all_table_data += [v.value]
        
        tf = TableFormatter(["Var", "Value"] + [col["title"] for col in extra_col_funcs] + ["Remark"])
        
        for item in vars_list:
            var_name = item.replace("{:", "{$") # mask formatting colon to avoid splitting the string in the wrong place
            var_parts = re.split(':', var_name.strip())
            if len(var_parts) > 1:
                var_name = var_parts[0].strip()
                title = var_parts[1].strip('"\'')
                title = title.replace("{$", "{:") # unmask colon and extract formatting if any
                title, fmt = self.get_formatting(title, fmt)
            else:
                title = ""
                fmt = ""
            
            var_name = var_name.strip()
            if var_name in self.context().get_vars():
                v = self.context().get_vars()[var_name]
                fmt = fmt or v.fmt
                # Add subsection for lists
                if type(v.value) == list:
                    tf.start_row_group(title or v.remark or var_name)
                    vals = []
                    for w in v.value:
                        if type(w) == tuple and len(w) > 1:
                            vals += [w[1]]                        
                            args = [w[1], [t[1] for t in v.value], all_table_data]
                            extra_cols = [invoke_table_fun(fn, args) for fn in extra_col_funcs]
                            title, fmt = self.get_formatting(w[2] if len(w) > 2 else "", fmt)
                            tf.add_row([self.format_and_prettify(w[0], w[0], fmt), 
                                        self.format_and_prettify(w[1], w[1], fmt)] + extra_cols + ([self.format_and_prettify(w[2], w[2], fmt)] if len(w) > 2 else []))
                        else:
                            vals += [w]
                            args = [w, v.value, all_table_data]
                            extra_cols = [invoke_table_fun(fn, args) for fn in extra_col_funcs]
                            tf.add_row(["", self.format_and_prettify(w, w, fmt)] + extra_cols)
                    for fn in sub_total_funcs:
                        tf.add_subtotal([fn['title'], invoke_table_fun(fn, [vals, all_table_data])])
                    tf.start_row_group()
                else:    
                    args = [v.value, non_stack_table_data, all_table_data]
                    extra_cols = [invoke_table_fun(fn, args) for fn in extra_col_funcs]
                    tf.add_row([v.var_name, self.format_and_prettify(v.value, v.value, fmt)] + extra_cols + [title])
            elif self.context().has_stack(var_name):
                stack = self.context().get_stack(var_name)
                stack_vars = stack.items
                stack_data = [v.value for v in stack_vars if v.var_name or self.SHOW_UNASSIGNED_VALUES_IN_TABLE]
                stack_fmt = stack.fmt    
                tf.start_row_group(title or stack.remark or var_name)
                for v in stack_vars:
                    item_fmt = fmt or v.fmt or stack_fmt
                    if v.var_name or self.SHOW_UNASSIGNED_VALUES_IN_TABLE:
                        args = [v.value, stack_data, all_table_data]
                        extra_cols = [invoke_table_fun(fn, args) for fn in extra_col_funcs]
                        tf.add_row([v.var_name if v.var_name else "", self.format_and_prettify(v.value, v.value, item_fmt)] + extra_cols + [v.remark])
                
                for fn in sub_total_funcs:
                    tf.add_subtotal([fn['title'], invoke_table_fun(fn, [stack_data, all_table_data])])
                tf.start_row_group()   

        if len(non_stack_table_data) > 0:
            for fn in sub_total_funcs:
                tf.add_subtotal([fn['title'], invoke_table_fun(fn, [non_stack_table_data, all_table_data])])

        for fn in total_funcs:
            tf.add_total([fn['title'], invoke_table_fun(fn, [all_table_data])])


        pos = line.end()
        # Erase the old table if it exists
        region = view.find("(\n*^\|.*)*", pos)
        if region:
            view.erase(edit, region)

        table = CR_LF + tf.format_table()
        pos += view.insert(edit, pos, table)
        return len(table)


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
