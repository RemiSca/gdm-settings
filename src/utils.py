'''Some random utility functions, classes, objects, etc. used throughout the source code'''

def getstdout(command, /):
    '''get standard output of a command'''

    from subprocess import run, PIPE
    if isinstance(command, str):
        command = command.split()
    return run(command, stdout=PIPE).stdout

def listdir_recursive(directory):
    """list files (only) inside a directory recursively"""

    from os import listdir, path

    files=[]
    for file in listdir(directory):
        if path.isdir(path.join(directory, file)):
            for subdir_file in listdir_recursive(path.join(directory, file)):
                files += [path.join(file, subdir_file)]
        else:
            files += [file]

    return files


def version(string, /):
    '''Return a tuple that represents a program version number'''

    return tuple(int(segment) for segment in string.split('.'))


class ProcessReturnCode(int):
    '''
    An integer that represents return code of a process

    bool(instance) returns True if value of instance is 0
    '''

    def __bool__ (self):
        return True if self == 0 else False

    @property
    def success (self):
        return bool(self)

    @property
    def failure (self):
        return not self.success

class NoCommandsFoundError(Exception): pass

class CommandElevator:
    """ Runs a list of commands with elevated privilages """
    def __init__(self, elevator:str='', *, shebang:str='') -> None:
        self.__list = []
        self.shebang = shebang or "#!/bin/sh"
        if elevator:
            self.elevator = elevator
        else:
            self.autodetect_elevator()

    @property
    def shebang(self):
        """ Shebang to determine shell for running elevated commands """
        return self.__shebang
    @shebang.setter
    def shebang(self, value):
        if value.startswith('#!/'):
            self.__shebang = value
        else:
            raise ValueError("shebang does not start with '#!/'")

    @property
    def elevator(self):
        """
        Program to use for privilage elevation

        Example: "sudo", "doas", "pkexec", etc.
        """
        return self.__elevator
    @elevator.setter
    def elevator(self, value):
        if isinstance(value, str):
            self.__elevator = value.strip(' ').split(' ')
        elif isinstance(value, list):
            self.__elevator = value
        else:
            raise ValueError("elevator is not of type 'str' or 'list'")

    @property
    def empty (self):
        return True if len(self.__list) == 0 else False

    def autodetect_elevator(self):
        from .enums import PackageType
        from . import env
        if env.PACKAGE_TYPE is PackageType.Flatpak:
            self.elevator = "flatpak-spawn --host pkexec"
        else:
            self.elevator = "pkexec"

    def add(self, command, /):
        """ Add a new command to the list """

        if isinstance(command, list):
            command = ' '.join(command)

        return self.__list.append(command)

    def clear(self):
        """ Clear command list """
        return self.__list.clear()

    def run_only(self) -> bool:
        """ Run commands but DO NOT clear command list """

        from os import chmod, makedirs, remove
        from subprocess import run
        from . import env

        returncode = 0
        if len(self.__list):
            makedirs(name=env.TEMP_DIR, exist_ok=True)
            script_file = f"{env.TEMP_DIR}/run-elevated"
            with open(script_file, "w") as open_script_file:
                print(self.__shebang, *self.__list, sep="\n", file=open_script_file)
            chmod(path=script_file, mode=755)
            returncode = run(args=[*self.__elevator, script_file]).returncode
            remove(script_file)

        return ProcessReturnCode(returncode)

    def run(self) -> bool:
        """ Run commands and clear command list"""

        if self.empty:
            raise NoCommandsFoundError(1, f'{self.__class__.__name__} instance has no commands to run')

        status = self.run_only()
        self.clear()
        return status
