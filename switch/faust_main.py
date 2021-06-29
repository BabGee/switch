import os, sys

print(__name__)
path = os.path.abspath(os.path.join(__file__, '..', '..'))
if path not in sys.path:
    sys.path.append(path)
print(path)

from switch.faust_app import app

#def main():
#    app.main()
#
#if __name__ == '__main__':
#    main()
app.main()
