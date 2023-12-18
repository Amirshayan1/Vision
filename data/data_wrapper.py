from pathlib import Path
import sys

# create absolute ROOT path object of model
ROOT = Path(__file__).resolve().parents[1]

# add ROOT to sys path
sys.path.append(str(ROOT))

from Utils.utils import parse_yaml

class Data:
    """
    dataset wrapper recieves data yaml file
    """
    def __init__(self, data_yaml):
        self.hyper = parse_yaml(data_yaml)
        self.class_names = self.hyper['class_names']

    def create_datasets(self, cls_num):
        """
        Creates train, valid and test sets
        """

        # check the class number with len of class names
        assert len(self.class_names) == cls_num, "create_datasets: ERROR: class names & number of classes are different!"

        # resolve the paths for train, val and test and make them absolute
        for x in "train_dir", "valid_dir", "test_dir":
            if self.hyper.get(x):
                if isinstance(self.hyper[x], str):
                    # resolve the path and store the string
                    self.hyper[x] = str((ROOT/self.hyper[x]).resolve())
                    print(self.hyper[x])

            else:
                print("create_datasets: ERROR: {} doest not exist in yaml!".format(x))
                # exit the program
                sys.exit(1)

        # return dataset dictionary   
        return self.hyper
