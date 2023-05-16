# Mathilda - a fancy SublimeText calculator plugin

This SublimeText3 plugin is inspired by the [SpeQ Mathematics](https://www.speqmath.com/) application.
It transforms your SublimeText editor into a powerful calculator/worksheet.

![SublimeText screenshot](img/screenshot-1.png "SublimeText screenshot")

## Installlation & quick start

* Put all files under the `$SUBLIME_SETTINGS/Packages/Mathilda` directory
* Start SublimeText editor
* Create a new file
* Set file syntax to **Mathilda** (Press `Ctrl-P`, type *Mathilda* and choose the *Set Syntax: Mathilda* menu item)
* Start typing an expression, then press `Enter` key
* The answer will automatically appear on the next line

## Features

### Basic math

```
1 + 2
      Answer = 3
1/9
			Answer = 0.1111111111111111      
Ans ** 2
			Answer = 0.012345679012345678
pi * 5**2
			Answer = 78.53981633974483    
1e6 + 1e7
			Answer = 11000000.0
```
### Basic complex math
```
1 + 2j
			Answer = (1+2j)
Ans / 2
			Answer = (0.5+1j)
```
### Math functions

All python built-in math functions are supported (see https://docs.python.org/3.6/library/math.html)
```
log10(100)
			Answer = 2.0
sin(pi/2)
			Answer = 1.0
degrees(pi)
			Answer = 180.0
factorial(27)
			Answer = 10888869450418352160768000000
```

### Percent arithmetic
```
100 + 17%
			Answer = 117.0
117 - 17%
			Answer = 97.11
25 * 20%
			Answer = 5.0
			
; 10% of what number will be 1?
1 / 10%
			Answer = 10.0
```

### Rational arithmetic

```
1:2
			Answer = 1/2
Ans +  3:8
			Answer = 7/8
Ans * 2
			Answer = 7/4
; Convert decimal value to rational
::.125
			Answer = 1/8
::3.14159265358979323
			Answer = 3126535/995207
pi -  3126535/995207 
			Answer = 1.1426415369442111e-12
; Back to decimals
1:3 + 1:3**2 + 1:3**3 + 1:3**4
			Answer = 40/81
Ans + 0.0
			Answer = 0.49382716049382713
```

### Date arithmetic
```
date(2019, 1, 1)
			Answer = 2019-01-01
today - ans
			Answer = 228 days, 0:00:00
Ans /4
			Answer = 57 days, 0:00:00
today + 1 year
			Answer = 2020-08-17
today + 1 month
			Answer = 2019-09-17
today + 1 week
			Answer = 2019-08-24
today + 1 day
			Answer = 2019-08-18
today + 24 hour
			Answer = 2019-08-18
```
### Variables

```
radius = 5
			Answer = 5
height = 5
			Answer = 5
volume = pi * radius**2 * height
			Answer = 392.69908169872417
```

### User-defined functions

```
volume(radius, height) = pi * radius**2 * height
			Answer = volume(radius, height) = pi * radius**2 * height

volume(5, 5)
			Answer = 392.69908169872417

c(n, k) = factorial(n) / (factorial (k) * factorial(n - k))
			Answer = c(n, k) = factorial(n) / (factorial (k) * factorial(n - k))
      
c(10, 5)
			Answer = 252.0
```

It's allowed to use built-in functions inside a custom function definition. Defining custom functions based on another custom functions is not supported.

### Named stacks

A worksheet may contain several named stacks. A named stack starts with the `@` character followed by a stack name. 
All calculations within the stack are collected into an array with the variable name corresponding to the stack name. Elements of this array can be accessed using the `[n]` syntax, or the variable can be passed to a function with an array argument (`sum()` or `prod()`). 

First stack element (with index 0) is always the last answer. Second stack element (with index 1) is the previous answer, etc. 

Example:

```
; Open a new stack
@supermarket

apples = 5.21
			Answer = 5.21
milk = 1.33
			Answer = 1.33

; When a line starts with '?', result is not saved into the stack
; '@@' always refers to the currently opened stack
? sum(@@) ; subtotal
			Answer = 6.54

; Open another stack
@diy

screwdriver = 17.95
			Answer = 17.95
hammer = 11.45
			Answer = 11.45
@total

sum(supermarket) + sum(diy)
			Answer = 35.94
```

### Anynymous stacks

By default an anonymous stack is created for the entire worksheet.

The `@@` variable refers to the entire stack, it can be passed to a function with an array argument, e.g. `sum(@@)` or `prod(@@)`.

It's also possible to access stack elements: 
* `@` references to the last answer
* `@0` references to the last answer stack item, i.e. the last answer
* `@1` references to the 1-st answer stack item
* `@2` references to the 2-nd answer stack item
* `@N` references to the N-th answer stack item

Example:

```
1
			Answer = 1
2
			Answer = 2
3
			Answer = 3
sum(@@)
			Answer = 6
; accessing the 4-th element of the (zero-based) stack
@3
			Answer = 1
```

### Comments

```
; end to line comment

# Heading level 1
## Heading level 2
### Heading level 3
#### Heading level 4
##### Heading level 5
###### Heading level 6
```

Comments also can be used to annotate and format variables as shown below:

```
apples = 5.21 ; golden + grany smith
			Answer = 5.21
milk = 1.33 ; 2.5 liter
			Answer = 1.33
```

This annotation is shown in the "Remark" colulmn in the table (see below)

Headings allow to navigate quickly through the worksheeet with the *Symbols* popup (`Ctrl + R`).

### Tables

! This is experimental feature and is subject of change in the future.

It's possible to display "report" tables built from variables: start a new line with the `!` character and enumerate variables to report. The table is partially compatible with Markdown syntax (exept the top and bottom lines).

```
apples = 5.21 ; golden + grany smith
			Answer = 5.21
milk = 1.33 ; 2.5 liter
			Answer = 1.33

screwdriver = 17.95 ; makita
			Answer = 17.95
hammer = 11.45
			Answer = 11.45
total = sum(@@)
			Answer = 35.94
! apples, milk, screwdriver, hammer, total
|--------------------------------------------|
| Var         | Value | Remark               |
|-------------|-------|----------------------|
| apples      |  5.21 | golden + grany smith |
| milk        |  1.33 | 2.5 liter            |
| screwdriver | 17.95 | makita               |
| hammer      | 11.45 |                      |
| total       | 35.94 |                      |
|--------------------------------------------|

```

## Useful shortcuts

* Press `F5` to recalculate entire worksheet (also happens on pressing the `Enter` key);
* To insert just a new line without recalculating use `Shift + Enter` shortcut;
* Press `F2` to display a list of defined variables;
* Start typing one of  `+`, `-`, `*`, or `/` characters on a new line to automatically use the previous answer;
* Comments and stacks are symbols, use CTRL+R to navigate the worksheet.
