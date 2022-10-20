"""
Helper functions for post-processing simulation outputs
"""

def format_axis(axis_handle, xlabel='', fontsize=18, linestyle='--', linewidth='1',
    color='grey', which='both', axis='y'):
    """Formats the axis"""
    # pylint: disable=too-many-arguments
    axis_handle.set_xlabel(xlabel)
    axis_handle.tick_params(axis='both', labelsize=fontsize)
    axis_handle.grid(
        visible=True,
        linestyle=linestyle,
        linewidth=linewidth,
        color=color,
        which=which,
        axis=axis
    )
    if xlabel=='':
        axis_handle.xaxis.set_ticklabels([])
    axis_handle.legend(fontsize=fontsize)

def annotate(axis_handle,text,major_offset,minor_offset, val):
    """Adds legend-like labels"""
    annotation_handle=axis_handle.annotate(
        text,
        xy=(val['position_x'], val['position_y']-val['major_offset']*major_offset-val['minor_offset']*minor_offset),
        xytext=(val['position_x'], val['position_y']-val['major_offset']*major_offset-val['minor_offset']*minor_offset),
        xycoords='subfigure fraction',
        fontsize=val['font_size'],
        alpha=val['alpha'],
    )
    annotation_handle.set_bbox(dict(facecolor='white', edgecolor='black', alpha=val['alpha'], linewidth=0,
        boxstyle='round,pad=0.1'))
