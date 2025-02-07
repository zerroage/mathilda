# Tables

1. Open a new tab in Sublime Text editor
2. Copy and paste the example code to the editor
3. Press `Ctrl+Shift+P` and select _Set syntax: Mathilda_ in the menu
4. Press `F5`

## Tables basics

A table directive starts with the `!` character followed by the comma-separated list of variables and, optionally, functions.

```
; Declare variables
a = 1

; Comments will be shown in the "Remark" column in the table
b = 2.71 ; Value of 'b'

; Comments may contain Python format string
c = 3.1415 ; Pi {:.2f}

; Show a, b, and c as a table
!a, b, c
```

For the format syntax see: https://docs.python.org/3/library/string.html#format-string-syntax

## Stacks and lists

Tables can be also generated for stacks and lists as shown below.

```
; Open a new stack
@mystack

; Anonymous value
1

; Variable
myvar = 2 ; Optional remark {:.2f}

; Hidden value starts with question mark `?`
?hidden_var = 3

; Generate a table for non-hidden values of the `mystack` stack
!mystack
```

> [!NOTE]
> 
> It's allowed to mix stacks, list and separate variables in one table. Non-stack variables are grouped into a separate _anonymous_ group to which subtotals aggregation functions are applied.


> [!NOTE]
> 
> An example of a table generated from a list can be found in the next section.


## Calculated colulmns

In addition to variables, stacks, and arrays, it is possible to display custom calculated columns using the following syntax:

```
!var1, var2, ..., c[olumn]:<custom_function_1>[:"Description and format"], c:<custom_function_2>[:"Description and format"], ...
```

The third part (_Description and format_) is optional.

The single-argument function can be custom-defined or be one of built-in functions.

Example:
```
; A list with the table data
my_data = [1, 2, 3]

; Define custom function for the calculated column. The comment text is shown 
; as a column name and the format string is used to format the value
my_fun(x) = 1/x ; My column {:.3f}

; Generate the table
!my_data, c:my_fun
```
### Custom column functions

Typically, a custom column function accepts two or three parameters:
* The scalar value of the row
* The list of all values in the group (stack or list)
* The list of all values in the table (optional)

One of examples of such a custom function is `bar` which is explained below in the last section.

## Subtotals and totals (table aggregation)

Subtotals and totals are also supported. Subtotals are calculated for _each_ group of data (stack or list), while totals are calculated for the entire table.

Syntax:
```
!var1, var2, ..., s[ubtotal]:<subtotal_function>[:"Description and format"], t[otal]:<total_function>[:"Description and format"], ...
```
The third part (_Description and format_) is optional.

Example:
```
; Define two datasets
dataset_1 = [1, 2, 3] ; Dataset #1
dataset_2 = [4, 5, 6] ; Dataset #2

; Generate the table for two datasets and subtotal and total rows
!dataset_1, dataset_2, s:sum:"Sum", t:sum:"Total sum", t:mean:"Total mean {:.3f}"
```

### Custom aggregation functions

It's also possible to define custom aggregation functions. Conventionally, the  function for _subtotals_ takes 2 arguments:

* The list of all values in group (stack or list)
* The list of all values in the table

The function for _totals_ takes 1 argument:
* The list of all values in the table
Example:

```
; Define two datasets
dataset_1 = [1, 2, 3] ; Dataset #1
dataset_2 = [4, 5, 6] ; Dataset #2

; Define custom subtotal function (`all_vals` is not used and can be omitted)
my_subtotal(group_vals, all_vals) = "Min:" + str(min(group_vals)) + ", Max:" + str(max(group_vals)); Min/max

my_total(all_vals) = min(all_vals) / max(all_vals) ; {:.2%} Ratio

; Generate the table
!dataset_1, dataset_2, s:my_subtotal, t:my_total
```

## Bar charts and custom bar function example

The built-in `bar` function can be used as a column-function and displays a bar chart based on the current row value and all group values. The bar length is proportional to the row value relative to all other values. 

Example:

```
; Define dataset
data = [10, 100, -15, 33, -21]

; Generate bar chart
!data, column:bar:"Bar chart"
```

### Custom bar chart function

In order to customize the bar chart layout, a custom function may be defined which calls the `bar` function.

The `bar` function parameters:

 *  `value`:        (positional) value in a table row
 *  `group_values`: (positional) list of values in the tables' group (a stack, or a list)
 *  `all_values`:   (positional) list of all values in the table (ignored)
 *  `size`:         table colulmn size, limits max bar size
 *  `base_value`:   base value for percent calculation, by default percentage is calculated from the maximum absolute value of all rows
 *  `mid_value`:    middle line value to generate two-directional bar chart
 *  `mid_char`:     symbol to draw the middle line
 *  `left_char`:    symbol to draw the left part of the bar chart with values less than mid_value
 *  `right_char`:   symbol to draw the right part of the bar chart with values greater than mid_value
 *  `left_tip`:     symbol to draw the tip of the left-side bar
 *  `right_tip`:    symbol to draw the tip of the right-side bar
 *  `left_fmt`:     Python format string to display value or percentage next to the left-side bar
 *  `right_fmt`:    Python format string to display value or percentage next to the right-side bar

Example: 
```
; A custom function used to display an angle in rational form
ang(x) = 1:12 * x

; Generate (variable, value, remark) tuples for the sine function using Python's for-comprehencion syntax:
plot_data = [(pi*x/12, sin(pi*x/12), str(ang(x)) + "·π") for x in range(0, 25)] ; Sine

; Define a custom plot function using the built-in `bar` function with customized argument values
plot(a, all) = bar(a, all, size=20, left_fmt = "", right_fmt = "", mid_char="", left_char=" ", left_tip="*", right_char=" ", right_tip="*", mid_value = 0)

!plot_data, c:plot
```

> [!NOTE]
> 
> The `bar` code snippet can be used for a custom bar chart function generation: type `Ctrl+Space` and choose `bar` from the list of snippets.