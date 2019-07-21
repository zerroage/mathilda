# sublime-calc

This SublimeText3 plugin is inspired by the [SpeQ Mathematics](https://www.speqmath.com/) application.
It transforms your SublimeText editor into a powerful calculator/worksheet.

![SublimeText screenshot](img/screenshot-1.png "SublimeText screenshot")

## How to install and use it

* Put all files under the `$SUBLIME_SETTINGS/Packages/sublime-calc` directory
* Start SublimeText3 editor
* Create a new file
* Set file syntax to **Worksheet**
* Start typing expressions, then press ENTER
* The answer will automatically appear on the next line

## Useful shortcuts

* Press F5 to recalculate entire worksheet
* Press F2 to display a list of defined variables
* Start typing a new line with + - * / to automatically use the previous answer
* Use CTRL+/ to comment/uncomment a line
* Comments are also symbols, use CTRL+R to navigate the worksheet

## Supported functions

All built-in Python functions, please refer to the `Worksheet.sublime-completions` file (or Python docs) for the complete list of built-in functions.

## Custom variables and functions

Define custom variable like this:

```
var = ... ; expression
```
Define custom function like  this:

```
fun(a, b, ...) = ... ; expression
```

It's allowed to use built-in functions inside a custom function definition. Defining custom functions based on another custom functions is not supported.
