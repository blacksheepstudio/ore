class bcolors:
    def cprint(self, text, color='white'):
        colors = {'purple': '\033[95m', 'blue': '\033[94m', 'green': '\033[92m',
                  'yellow': '\033[93m', 'red': '\033[91m', 'white': '\033[0m',
                  'bold': '\033[1m', 'underline': '\033[4m'}
        print('{0}{1}{2}'.format(colors[color], text, colors['white']))