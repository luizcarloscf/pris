# The terminal

Every other guide types commands. This one explains what that means: what a terminal is, how to move between folders, create and edit files, install programs and stop one that runs. It assumes only an Ubuntu computer, freshly installed.

!!! info "To learn more"

    - [The Linux command line for beginners](https://ubuntu.com/tutorials/command-line-for-beginners): Ubuntu's own tutorial;
    - [The Linux Command Line](https://linuxcommand.org/tlcl.php), by William Shotts: a free book, from the first command to writing scripts.

## What a terminal is

Programs with windows and buttons are one way to use a computer. The **terminal** is another: you type a **command**, press Enter, and the computer runs it and prints its answer as text. It looks old-fashioned, but it is how programmers work: a command can be copied, repeated, combined with others and written down in a guide like this one, which a click can't.

Open it with ++ctrl+alt+t++, or by searching "Terminal" in the applications. A window appears with a line such as:

```
student@lab-pc:~$
```

That line is the **prompt**: the terminal is waiting for a command. It shows who you are (`student`), the computer's name (`lab-pc`) and where you are (`~`, explained below). The `$` ends it. In the guides, commands are written without the prompt: type only what follows it.

Try one: type `date` and press Enter. The terminal prints the date and time, then a new prompt.

## Files and folders

The computer keeps everything in **files**, inside **folders** (also called **directories**), which can hold other folders. The topmost folder is `/`, the **root**. Your own files live in your **home folder**, `/home/<your user name>`, written `~` for short.

The terminal is always "in" one folder, the **current folder**. A few commands move around and look:

```shell
pwd                    # print the current folder: /home/student
ls                     # list what is in it: Desktop  Documents  Downloads ...
cd Documents           # change into the Documents folder
pwd                    # /home/student/Documents
cd ..                  # go up one level, back to /home/student
cd ~                   # go home, from anywhere
```

Everything after a `#` is a **comment**: it explains the command and is ignored by the computer. You can paste a line with its comment and it still works.

A **path** names a file or folder. `/home/student/Documents/report.txt` is an **absolute** path, from the root. `Documents/report.txt` is **relative**: it starts from the current folder. `..` means "the folder above" and `.` means "this folder".

## Creating and changing files

```shell
mkdir notes            # make a new folder, notes
cd notes
echo "first line" > todo.txt       # write a line into a new file, todo.txt
echo "second line" >> todo.txt     # add a line at its end
cat todo.txt           # show what is in it
cp todo.txt copy.txt   # copy it
mv copy.txt old.txt    # move it, which also renames it
rm old.txt             # remove it: there is no trash bin, it is gone
ls
```

`>` sends what a command prints into a file, replacing what was there; `>>` adds to the end instead. Be careful with `rm`: the terminal never asks "are you sure?".

To write longer files, such as the programs of the next guides, use a **text editor**. Ubuntu comes with the Text Editor in its applications, and `nano` in the terminal: `nano todo.txt` opens the file, you type, ++ctrl+o++ then Enter saves, and ++ctrl+x++ quits. Many programmers use [Visual Studio Code](https://code.visualstudio.com/docs/setup/linux), which shows a file and a terminal side by side.

## Commands and their options

A command is a program's name, followed by **arguments**, the things it works on, and **options**, which change how it works and start with `-` or `--`:

```shell
ls -l                  # -l: the long listing, with sizes and dates
ls -a                  # -a: also the hidden files, whose names start with a dot
ls --help              # what options ls has
man ls                 # its full manual: arrows to scroll, q to quit
```

A few keys save a lot of typing:

| Key | What it does |
|---|---|
| ++tab++ | completes a command or a file name: type `cd Doc` and Tab |
| ++arrow-up++ / ++arrow-down++ | brings back the previous commands |
| ++ctrl+c++ | stops the command that is running |
| ++ctrl+shift+c++ / ++ctrl+shift+v++ | copy and paste, in the terminal (++ctrl+c++ alone stops a command) |
| ++ctrl+l++ | clears the screen |

Many guides ask you to keep a program running in one terminal while you type in another: open a new terminal tab with ++ctrl+shift+t++.

## Installing programs

Ubuntu installs programs with **apt**, from its own collection of packages. Installing changes the whole computer, so it needs the administrator's permission, given by **sudo**: it runs the command after it as the administrator, and asks for your password the first time (nothing shows on the screen while you type it; that is normal).

```shell
sudo apt update                    # refresh the list of available packages
sudo apt install -y curl git       # install two programs; -y answers "yes" for you
curl --version                     # check that it works
```

`which curl` tells where an installed program is, and nothing if it isn't installed.

## Running programs and scripts

Any program is run by typing its name: `python3`, `curl`, `git`. A program in the current folder is run with its path, such as `./hello.sh`. A **script** is a text file of commands; save this as `hello.sh`:

```shell
#!/bin/sh
echo hello from a script
```

```shell
chmod +x hello.sh      # mark it as a program that can be run
./hello.sh             # hello from a script
```

The first line, `#!/bin/sh`, says which program reads the file; `chmod +x` gives it permission to run.

## Environment variables

The terminal keeps a few named settings, **environment variables**, that programs read. `echo $HOME` shows one, your home folder. `PATH` lists the folders where the terminal looks for programs when you type a name: `echo $PATH`. Setting one for a single command is common in the guides: `GREETING=hi python3 app.py` runs the program with `GREETING` set to `hi`.

## When something goes wrong

| Message | What it means |
|---|---|
| `command not found` | the program isn't installed, or its name is mistyped |
| `No such file or directory` | the path is wrong: check it with `pwd` and `ls` |
| `Permission denied` | you may not do that: it needs `sudo`, or the file isn't marked runnable (`chmod +x`) |
| the terminal stops answering | a program is still running: wait, or stop it with ++ctrl+c++ |

Read error messages: they almost always say what is wrong, and pasting one into a search engine usually finds the answer.

## What you learned

- The terminal runs commands you type; the prompt shows it is waiting.
- `pwd`, `ls` and `cd` look around and move; paths are absolute (from `/`) or relative (from where you are).
- `mkdir`, `echo >`, `cat`, `cp`, `mv` and `rm` create and change files; an editor writes longer ones.
- `sudo apt install` installs programs; ++ctrl+c++ stops one.
