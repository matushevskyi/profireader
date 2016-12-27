import sys

sys.path.append('..')
import pstats
import argparse


parser = argparse.ArgumentParser(description='view profile')
parser.add_argument("file", help="file to view")
p = pstats.Stats('../log/profi.prof')
p.sort_stats('calls')
p.print_stats()