"""

Module to present a base neuroimaging scan, currently T1 mri, without any overlay.

"""

import argparse
import sys
import textwrap
from abc import abstractmethod
from os.path import join as pjoin
import warnings
from visualqc import config as cfg
from visualqc.workflows import BaseWorkflow
from visualqc.interfaces import BaseReviewInterface
from visualqc.utils import check_id_list, check_input_dir, check_views, check_finite_int, check_out_dir, check_outlier_params, get_path_for_subject, \
    read_image, scale_0to1, pick_slices, get_axis
from mrivis.utils import crop_image
import numpy as np
from matplotlib import pyplot as plt, colors, cm
from matplotlib.widgets import CheckButtons
from os import makedirs
from os.path import join as pjoin, exists as pexists
from shutil import copyfile, which

class T1MriInterface(BaseReviewInterface):
    """Custom interface for rating the quality of T1 MRI scan."""


    def __init__(self,
                 fig,
                 axes,
                 issue_list=cfg.t1_mri_default_issue_list):
        """Constructor"""

        super().__init__(fig, axes)

        self.issue_list = issue_list


    def add_checkboxes(self):
        """
        Checkboxes offer the ability to select multiple tags such as Motion, Ghosting Aliasing etc,
            instead of one from a list of mutual exclusive rating options (such as Good, Bad, Error etc).

        """

        ax_checkbox = plt.axes(cfg.position_rating_axis,
                               facecolor=cfg.color_rating_axis, aspect='equal')
        self.checkbox = CheckButtons(ax_checkbox, labels=self.issue_list, actives=None)
        self.checkbox.on_clicked(self.save_issues)
        for txt_lbl in self.checkbox.labels:
            txt_lbl.set(color=cfg.text_option_color, fontweight='normal')

        for rect in self.checkbox.rectangles:
            rect.set_width(cfg.checkbox_rect_width)


    def save_issues(self, labels):
        """Update the rating"""

        # print('  rating {}'.format(label))
        self.user_rated_issues = labels

    def capture_user_input(self):
        """Saves all user input, such as rating/issues/notes etc"""

        return self.user_notes, self.user_rated_issues

    def reset_figure(self):
        "Resets the figure to prepare it for display of next subject."

        self.clear_all_axes()
        self.clear_checkboxes()

    def clear_all_axes(self):
        """clearing all axes"""

        for ax in self.axes:
            ax.cla()

    def clear_checkboxes(self):
        """Clears all checkboxes"""

        cbox_statuses = self.checkbox.get_status()
        for index in range(len(self.issue_list)):
            # if it was selected already, toggle it.
            if cbox_statuses[index]:
                # set_active() is actually a toggle() operation
                self.checkbox.set_active(index)


class RatingWorkflowT1(BaseWorkflow):
    """
    Rating workflow without any overlay.
    """


    def __init__(self,
                 id_list,
                 in_dir,
                 out_dir,
                 issue_list,
                 mri_name,
                 outlier_method, outlier_fraction,
                 outlier_feat_types, disable_outlier_detection,
                 prepare_first,
                 vis_type,
                 views, num_slices_per_view, num_rows_per_view):
        """Constructor"""

        super().__init__(id_list, in_dir, out_dir,
                         outlier_method, outlier_fraction,
                         outlier_feat_types, disable_outlier_detection)

        self.vis_type = vis_type
        self.issue_list = issue_list
        self.mri_name = mri_name
        self.expt_id = 'rate_mri_{}'.format(self.mri_name)

        self.init_layout(views, num_rows_per_view, num_slices_per_view)

        self.prepare_first = prepare_first

        from visualqc.features import extract_T1_features
        self.feature_extractor = extract_T1_features


    def run(self):
        """Generate the required visualizations for the specified subjects."""

        self.preprocess()
        self.prepare_UI()
        self.loop_through_subjects()

        return

    def preprocess(self):
        """
        Preprocess the input data
            e.g. compute features, make complex visualizations etc.
            before starting the review process.
        """

        print('Preprocessing data - please wait .. '
              '\n\t(or contemplate the vastness of universe! )')
        self.extract_features()
        self.detect_outliers()
        self.restore_ratings()

        # no complex vis to generate - skipping

    def prepare_UI(self):
        """Main method to run the entire workflow"""

        self.open_figure()
        self.add_UI()

    def init_layout(self, views, num_rows_per_view,
                    num_slices_per_view, padding=cfg.default_padding):

        self.views = views
        self.num_slices_per_view = num_slices_per_view
        self.num_rows_per_view = num_rows_per_view
        self.num_rows = len(self.views)*self.num_rows_per_view
        self.num_cols = int((len(self.views) * self.num_slices_per_view) / self.num_rows)
        self.padding = padding

    def open_figure(self):
        """Creates the master figure to show everything in."""

        self.figsize = [15, 12]
        self.fig = plt.figure(figsize=self.figsize)
        self.fig, self.axes = plt.subplots(self.num_rows, self.num_cols, figsize=self.figsize)
        self.axes = self.axes.flatten()
        plt.style.use('dark_background')
        self.display_params = dict(interpolation='none', aspect='equal',
                              origin='lower', cmap='gray')

    def restore_ratings(self):
        """Restores any ratings from previous sessions."""

        from visualqc.utils import restore_previous_ratings
        self.ratings, self.notes, self.incomplete_list = restore_previous_ratings(self)

    def add_UI(self):
        """Adds the review UI with defaults"""

        self.UI = T1MriInterface(self.fig, self.axes, self.issue_list)

    def save_ratings(self):
        """Saves ratings to disk """

        ratings_dir = pjoin(self.out_dir, cfg.suffix_ratings_dir)
        if not pexists(ratings_dir):
            makedirs(ratings_dir)

        file_name_ratings = '{}_{}'.format(self.vis_type, cfg.file_name_ratings)
        ratings_file = pjoin(ratings_dir, file_name_ratings)
        prev_ratings_backup = pjoin(ratings_dir, '{}_{}'.format(cfg.prefix_backup, file_name_ratings))
        if pexists(ratings_file):
            copyfile(ratings_file, prev_ratings_backup)

        # TODO t1 rating is a list of items, not a single string, handle it
        # add column names: subject_id,issue1,issue2,...,notes etc
        lines = '\n'.join(['{},{},{}'.format(sid, rating, self.notes[sid]) for sid, rating in self.ratings.items()])
        try:
            with open(ratings_file, 'w') as cf:
                cf.write(lines)
        except:
            raise IOError(
                'Error in saving ratings to file!!\nBackup might be helpful at:\n\t{}'.format(prev_ratings_backup))

    def loop_through_subjects(self):
        """Workhorse for the workflow!"""

        for subject_id in self.incomplete_list:
            self.current_subject_id = subject_id
            flagged_as_outlier = subject_id in self.by_sample
            alerts_outlier = self.by_sample.get(subject_id, None)  # None, if id not in dict
            outlier_alert_msg = '\n\tFlagged as a possible outlier ' \
                                'by these measures:\n\t{}'.format(alerts_outlier) \
                                    if flagged_as_outlier else ' '
            print('\nReviewing {} {}'.format(subject_id, outlier_alert_msg))
            t1_mri, out_path, skip_subject = self.load_data(subject_id)

            if skip_subject:
                print('Skipping current subject ..')
                continue

            self.display_slices(t1_mri)

            # TODO updating ratings/notes etc needs to be worked out
            self.capture_user_input(subject_id)
            # self.ratings[subject_id], self.notes[subject_id], self.quit_now

            # informing only when it was rated!
            if self.ratings[subject_id] not in cfg.ratings_not_to_be_recorded:
                print('id {} rating {} notes {}'.format(subject_id,
                                                        self.ratings[subject_id],
                                                        self.notes[subject_id]))
            else:
                self.ratings.pop(subject_id)

            if self.UI.quit_now:
                print('\nUser chosen to quit..')
                break

        print('Saving ratings .. \n')
        self.save_ratings()

    def capture_user_input(self, subject_id):
        """Updates all user input to class"""

        self.ratings[subject_id] = self.UI.user_rated_issues
        self.notes[subject_id] = self.UI.user_notes

    def load_data(self, subject_id):
        """Loads the image data for display."""

        t1_mri_path = get_path_for_subject(self.in_dir, subject_id, self.mri_name, self.vis_type)
        t1_mri = read_image(t1_mri_path, error_msg='T1 mri')

        skip_subject = False
        if np.count_nonzero(t1_mri)==0:
            skip_subject = True
            print('MR image is empty!')
            out_vis_path = None
        else:
            # where to save the visualization to
            out_vis_path = pjoin(self.out_dir, 'visual_qc_{}_{}'.format(self.vis_type, subject_id))

        return t1_mri, out_vis_path, skip_subject

    def display_slices(self, img):
        """Adds slice collage to the given axes"""

        # crop and rescale
        img = crop_image(img, self.padding)
        img = scale_0to1(img)

        slices = pick_slices(img, self.views, self.num_slices_per_view)
        for ax_counter, (dim_index, slice_num) in enumerate(slices):
            plt.sca(self.axes[ax_counter])
            slice1 = get_axis(img, dim_index, slice_num)
            plt.imshow(slice1, **self.display_params)
            plt.axis('off')


def get_parser():
    """Parser to specify arguments and their defaults."""

    parser = argparse.ArgumentParser(prog="T1_mri_visualqc",
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     description='T1_mri_visualqc: rate quality of anatomical MR scan.')

    help_text_fs_dir = textwrap.dedent("""
    Absolute path to ``SUBJECTS_DIR`` containing the finished runs of Freesurfer parcellation
    Each subject will be queried after its ID in the metadata file.

    E.g. ``--fs_dir /project/freesurfer_v5.3``
    \n""")

    help_text_user_dir = textwrap.dedent("""
    Absolute path to an input folder containing the MRI scan. 
    Each subject will be queried after its ID in the metadata file, 
    and is expected to have the MRI (specified ``--mri_name``), 
    in its own folder under --user_dir.

    E.g. ``--user_dir /project/images_to_QC``
    \n""")

    help_text_id_list = textwrap.dedent("""
    Abs path to file containing list of subject IDs to be processed.
    If not provided, all the subjects with required files will be processed.

    E.g.

    .. parsed-literal::

        sub001
        sub002
        cn_003
        cn_004

    \n""")

    help_text_out_dir = textwrap.dedent("""
    Output folder to store the visualizations & ratings.
    Default: a new folder called ``{}`` will be created inside the ``fs_dir``
    \n""".format(cfg.default_out_dir_name))

    help_text_views = textwrap.dedent("""
    Specifies the set of views to display - could be just 1 view, or 2 or all 3.
    Example: --views 0 (typically sagittal) or --views 1 2 (axial and coronal)
    Default: {} {} {} (show all the views in the selected segmentation)
    \n""".format(cfg.default_views[0], cfg.default_views[1], cfg.default_views[2]))

    help_text_num_slices = textwrap.dedent("""
    Specifies the number of slices to display per each view. 
    This must be even to facilitate better division.
    Default: {}.
    \n""".format(cfg.default_num_slices))

    help_text_num_rows = textwrap.dedent("""
    Specifies the number of rows to display per each axis. 
    Default: {}.
    \n""".format(cfg.default_num_rows))

    help_text_prepare = textwrap.dedent("""
    This flag enables batch-generation of 3d surface visualizations, prior to starting any review and rating operations. 
    This makes the switch from one subject to the next, even more seamless (saving few seconds :) ).

    Default: False (required visualizations are generated only on demand, which can take 5-10 seconds for each subject).
    \n""")

    help_text_outlier_detection_method = textwrap.dedent("""
    Method used to detect the outliers.

    For more info, read http://scikit-learn.org/stable/modules/outlier_detection.html

    Default: {}.
    \n""".format(cfg.default_outlier_detection_method))

    help_text_outlier_fraction = textwrap.dedent("""
    Fraction of outliers expected in the given sample. Must be >= 1/n and <= (n-1)/n, 
    where n is the number of samples in the current sample.

    For more info, read http://scikit-learn.org/stable/modules/outlier_detection.html

    Default: {}.
    \n""".format(cfg.default_outlier_fraction))

    help_text_outlier_feat_types = textwrap.dedent("""
    Type of features to be employed in training the outlier detection method.  It could be one of  
    'cortical' (aparc.stats: mean thickness and other geometrical features from each cortical label), 
    'subcortical' (aseg.stats: volumes of several subcortical structures), 
    or 'both' (using both aseg and aparc stats).

    Default: {} {}.
    \n""".format(cfg.freesurfer_features_outlier_detection[0], cfg.freesurfer_features_outlier_detection[1]))

    help_text_disable_outlier_detection = textwrap.dedent("""
    This flag disables outlier detection and alerts altogether.
    \n""")

    in_out = parser.add_argument_group('Input and output', ' ')

    in_out.add_argument("-i", "--id_list", action="store", dest="id_list",
                        default=None, required=False, help=help_text_id_list)

    in_out.add_argument("-u", "--user_dir", action="store", dest="user_dir",
                        default=cfg.default_user_dir,
                        required=False, help=help_text_user_dir)

    in_out.add_argument("-o", "--out_dir", action="store", dest="out_dir",
                        required=False, help=help_text_out_dir,
                        default=None)

    in_out.add_argument("-f", "--fs_dir", action="store", dest="fs_dir",
                        default=cfg.default_freesurfer_dir,
                        required=False, help=help_text_fs_dir)
    outliers = parser.add_argument_group('Outlier detection',
                                         'options related to automatically detecting possible outliers')
    outliers.add_argument("-olm", "--outlier_method", action="store", dest="outlier_method",
                          default=cfg.default_outlier_detection_method, required=False,
                          help=help_text_outlier_detection_method)

    outliers.add_argument("-olf", "--outlier_fraction", action="store", dest="outlier_fraction",
                          default=cfg.default_outlier_fraction, required=False,
                          help=help_text_outlier_fraction)

    outliers.add_argument("-olt", "--outlier_feat_types", action="store", dest="outlier_feat_types",
                          default=cfg.freesurfer_features_outlier_detection, required=False,
                          help=help_text_outlier_feat_types)

    outliers.add_argument("-old", "--disable_outlier_detection", action="store_true",
                          dest="disable_outlier_detection",
                          required=False, help=help_text_disable_outlier_detection)

    layout = parser.add_argument_group('Layout options', ' ')
    layout.add_argument("-w", "--views", action="store", dest="views",
                        default=cfg.default_views, required=False, nargs='+',
                        help=help_text_views)

    layout.add_argument("-s", "--num_slices", action="store", dest="num_slices",
                        default=cfg.default_num_slices, required=False,
                        help=help_text_num_slices)

    layout.add_argument("-r", "--num_rows", action="store", dest="num_rows",
                        default=cfg.default_num_rows, required=False,
                        help=help_text_num_rows)

    wf_args = parser.add_argument_group('Workflow', 'Options related to workflow '
                                                    'e.g. to pre-compute resource-intensive features, '
                                                    'and pre-generate all the visualizations required')
    wf_args.add_argument("-p", "--prepare_first", action="store_true", dest="prepare_first",
                         help=help_text_prepare)

    return parser


def make_workflow_from_user_options():
    """Parser/validator for the cmd line args."""

    parser = get_parser()

    if len(sys.argv) < 2:
        print('Too few arguments!')
        parser.print_help()
        parser.exit(1)

    # parsing
    try:
        user_args = parser.parse_args()
    except:
        parser.exit(1)

    vis_type = None

    in_dir, source_of_features = check_input_dir(user_args.fs_dir, user_args.user_dir, vis_type)

    mri_name = user_args.mri_name
    seg_name = user_args.seg_name
    id_list, images_for_id = check_id_list(user_args.id_list, in_dir, vis_type, mri_name, seg_name)

    out_dir = check_out_dir(user_args.out_dir, in_dir)
    views = check_views(user_args.views)

    num_slices_per_view, num_rows_per_view = check_finite_int(user_args.num_slices, user_args.num_rows)

    outlier_method, outlier_fraction, \
    outlier_feat_types, disable_outlier_detection = check_outlier_params(user_args.outlier_method,
                                                                         user_args.outlier_fraction,
                                                                         user_args.outlier_feat_types,
                                                                         user_args.disable_outlier_detection,
                                                                         id_list, source_of_features)

    wf = RatingWorkflowT1(id_list, in_dir, out_dir,
                          cfg.t1_mri_default_issue_list,
                          mri_name,
                          outlier_method, outlier_fraction,
                          outlier_feat_types, disable_outlier_detection,
                          user_args.prepare_first,
                          vis_type,
                          views, num_slices_per_view, num_rows_per_view)

    return wf


def cli_run():
    """Main entry point."""

    wf = make_workflow_from_user_options()

    if wf.vis_type is not None:
        # matplotlib.interactive(True)
        wf.run()
        print('Results are available in:\n\t{}'.format(wf.out_dir))
    else:
        raise ValueError('Invalid state for visualQC!\n'
                         '\t Ensure proper combination of arguments is used.')

    return


if __name__ == '__main__':
    # disabling all not severe warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)

        cli_run()
