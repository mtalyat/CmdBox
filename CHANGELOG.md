# Changelog

## 1.0.5
- Allow keyboard shortcuts to use other keys, including punctuation such as '/'.

## 1.0.4
- The title of the command now shows up in the Command Arguments dialog box.
- Adjust Command Arguments dialog box text.
- Command Arguments now have different types. They can be used like so: {ArgName:type,arg1,arg2,...,argn}. Types:
    - text (default if omitted)
    - int,starting_value=0,increment_amount=1
    - dec,starting_value=0,increment_amount=0.1
    - list,list_item_1,list_item_2,...,list_item_n
    - check,checked,int
        - Starts as checked when 'checked' is present
        - Returns a value of '1' or '0' instead of 'true' and 'false' when 'int' is present
    - path,extensions,file/directory,multiple
        - Extensions use the OS extension format, such as (\*.txt)|\*.txt. Separated by ;
        - file or directory, determines if searching for files or directories. Defaults to file.
        - multiple allows for multiple items to be selected.
- The command text box is now bigger when editing a command button.
- Command button text now has word wrapping.
- Add option to define the success value in order for an Error to show.

## 1.0.3
- Show errors now defaults to off.

## 1.0.2
- Add show cmdbox checkbox for commands.
- Change it so the output box size is modifyable.

## 1.0.1
- Add optional error popups on command fail.
- Popup appears on top even if the window is not minimized.

## 1.0.0
- Initial release.