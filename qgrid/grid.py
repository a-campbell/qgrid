import pandas as pd
import numpy as np
import uuid
import os
import json
from numbers import Integral

from IPython.display import display_html, display_javascript
try:
    from ipywidgets import widgets
except ImportError:
    from IPython.html import widgets
from IPython.display import display, Javascript, clear_output


try:
    from traitlets import Unicode, Instance, Bool, Integer, Dict
except ImportError:
    from IPython.utils.traitlets import Unicode, Instance, Bool, Integer, Dict


def template_contents(filename):
    template_filepath = os.path.join(
        os.path.dirname(__file__),
        'templates',
        filename,
    )
    with open(template_filepath) as f:
        return f.read()


SLICK_GRID_CSS = template_contents('slickgrid.css.template')
SLICK_GRID_JS = template_contents('slickgrid.js.template')
REMOTE_URL = ("https://cdn.rawgit.com/quantopian/qgrid/"
              "master/qgrid/qgridjs/")


class _DefaultSettings(object):

    def __init__(self):
        self._grid_options = {
            'fullWidthRows': True,
            'syncColumnCellResize': True,
            'forceFitColumns': True,
            'rowHeight': 28,
            'enableColumnReorder': False,
            'enableTextSelectionOnCells': True,
            'editable': True,
            'autoEdit': False
        }
        self._remote_js = False
        self._precision = None  # Defer to pandas.get_option

    def set_grid_option(self, optname, optvalue):
        self._grid_options[optname] = optvalue

    def set_defaults(self, remote_js=None, precision=None, grid_options=None):
        if remote_js is not None:
            self._remote_js = remote_js
        if precision is not None:
            self._precision = precision
        if grid_options is not None:
            self._grid_options = grid_options

    @property
    def grid_options(self):
        return self._grid_options

    @property
    def remote_js(self):
        return self._remote_js

    @property
    def precision(self):
        return self._precision or pd.get_option('display.precision') - 1

defaults = _DefaultSettings()

def set_defaults(remote_js=None, precision=None, grid_options=None):
    """
    Set the default qgrid options.  The options that you can set here are the
    same ones that you can pass into ``show_grid``.  See the documentation
    for ``show_grid`` for more information.

    Notes
    -----
    This function will be useful to you if you find yourself
    setting the same options every time you make a call to ``show_grid``.
    Calling this ``set_defaults`` function once sets the options for the
    lifetime of the kernel, so you won't have to include the same options
    every time you call ``show_grid``.

    See Also
    --------
    show_grid :
        The function whose default behavior is changed by ``set_defaults``.
    """
    defaults.set_defaults(remote_js, precision, grid_options)

def set_grid_option(optname, optvalue):
    """
    Set the default value for one of the options that gets passed into the
    SlickGrid constructor.

    Parameters
    ----------
    optname : str
        The name of the option to set.
    optvalue : object
        The new value to set.

    Notes
    -----
    The options you can set here are the same ones
    that you can set via the ``grid_options`` parameter of the ``set_defaults``
    or ``show_grid`` functions.  See the `SlickGrid documentation
    <https://github.com/mleibman/SlickGrid/wiki/Grid-Options>`_ for the full
    list of available options.
    """
    self._grid_options[optname] = optvalue

def show_grid(data, remote_js=None, precision=None, grid_options=None,
              show_toolbar=False, call_function_on_row_data=None):
    """
    Main entry point for rendering DataFrames as SlickGrids.

    Parameters
    ----------
    remote_js : bool
        Whether to load slickgrid.js from a local filesystem or from a
        remote CDN.  Loading from the local filesystem means that SlickGrid
        will function even when not connected to the internet, but grid
        cells created with local filesystem loading will not render
        correctly on external sharing services like NBViewer.
    precision : integer
        The number of digits of precision to display for floating-point
        values.  If unset, we use the value of
        `pandas.get_option('display.precision')`.
    grid_options : dict
        Options to use when creating javascript SlickGrid instances.  See
        the `SlickGrid documentation <https://github.com/mleibman/SlickGrid/wiki/Grid-Options>`_ for
        information on the available options.  See the Notes section below for
        the list of options that qgrid sets by default.

    Notes
    -----
    By default, the following options get passed into SlickGrid when
    ``show_grid`` is called.  See the `SlickGrid documentation
    <https://github.com/mleibman/SlickGrid/wiki/Grid-Options>`_ for information
    about these options.
    ::
        {
            'fullWidthRows': True,
            'syncColumnCellResize': True,
            'forceFitColumns': True,
            'rowHeight': 28,
            'enableColumnReorder': False,
            'enableTextSelectionOnCells': True,
            'editable': True,
            'autoEdit': False
        }
    show_toolbar: bool
        Whether to show a toolbar with options for adding/removing rows and
        exporting the widget to a static view.


    See Also
    --------
    set_defaults : Permanently set global defaults for `show_grid`.
    set_grid_option : Permanently set individual SlickGrid options.
    """

    if remote_js is None:
        remote_js = defaults.remote_js
    if precision is None:
        precision = defaults.precision
        if not isinstance(precision, Integral):
            raise TypeError("precision must be int, not %s" % type(precision))
    if grid_options is None:
        grid_options = defaults.grid_options
        if not isinstance(grid_options, dict):
            raise TypeError(
                "grid_options must be dict, not %s" % type(grid_options)
            )
    data_obj = data

    grid = QGridWidget(df=data_obj, precision=precision,
                       grid_options=json.dumps(grid_options),
                       remote_js=remote_js)

    if show_toolbar:
        add_row = widgets.Button(description="Add Row")
        add_row.on_click(grid.add_row)

        rem_row = widgets.Button(description="Remove Row")
        rem_row.on_click(grid.remove_row)

        export = widgets.Button(description="Export")
        export.on_click(grid.export)

        get_f = widgets.Button(description='Get Filters')
        get_f.on_click(grid.get_filters)

        if call_function_on_row_data is not None:
            run_function = widgets.Button(description=call_function_on_row_data[0])
            grid.user_function = call_function_on_row_data[1]
            run_function.on_click(grid.get_data_and_call_function)
            display(widgets.HBox((add_row, rem_row, export, run_function, get_f)), grid)

        else:
            display(widgets.HBox((add_row, rem_row, export)), grid)
    else:
        # display(grid)
        return grid


class QGridWidget(widgets.DOMWidget):
    _view_module = Unicode("nbextensions/qgridjs/qgrid.widget", sync=True)
    _view_name = Unicode('QGridView', sync=True)
    _df_json = Unicode('', sync=True)
    _column_types_json = Unicode('', sync=True)
    _index_name = Unicode('')
    _cdn_base_url = Unicode("/nbextensions/qgridjs", sync=True)
    _multi_index = Bool(False)

    # bz_data = Instance(bz.expr.expressions.Slice)
    df = Instance(pd.DataFrame)
    precision = Integer()
    grid_options = Unicode('', sync=True)
    remote_js = Bool(True)
    selected_row = Dict({}, sync=True)
    selected_id = Integer(0, sync=True)

    def _df_changed(self):
        """Build the Data Table for the DataFrame."""

        # register a callback for custom messages
        df = self.df
        self.on_msg(self._handle_qgrid_msg)


        if not df.index.name:
            df.index.name = 'Index'

        self._index_name = df.index.name

        tc = dict(np.typecodes)
        for key in np.typecodes.keys():
            if "All" in key:
                del tc[key]

        column_types = []
        for col_name, dtype in df.dtypes.iteritems():
            if str(dtype) == 'category':
                categories = list(df[col_name].cat.categories)
                column_type = {'field': col_name,
                               'categories': ','.join(categories)}
                # XXXX: work around bug in to_json for categorical types
                # https://github.com/pydata/pandas/issues/10778
                df[col_name] = df[col_name].astype(str)
                column_types.append(column_type)
                break
            column_type = {'field': col_name}
            for type_name, type_codes in tc.items():
                if dtype.kind in type_codes:
                    column_type['type'] = type_name
                    break
            column_types.append(column_type)
        self._column_types_json = json.dumps(column_types)

        self._df_json = df.to_json(
                orient='records',
                date_format='iso',
                double_precision=self.precision,
            )

        self._remote_js_changed()

    def _remote_js_changed(self):
        if self.remote_js:
            self._cdn_base_url = REMOTE_URL
        else:
            self._cdn_base_url = "/nbextensions/qgridjs"

    def add_row(self, value=None):
        """Append a row at the end of the dataframe."""
        df = self.df
        if not df.index.is_integer():
            msg = "Cannot add a row to a table with a non-integer index"
            display(Javascript('alert("%s")' % msg))
            return
        last = df.iloc[-1]
        last.name += 1
        df.loc[last.name] = last.values
        precision = pd.get_option('display.precision') - 1
        row_data = last.to_json(date_format='iso',
                                double_precision=precision)
        msg = json.loads(row_data)
        msg[self._index_name] = str(last.name)
        msg['id'] = str(last.name)
        msg['type'] = 'add_row'
        self.send(msg)

    def remove_row(self, value=None):
        """Remove the current row from the table"""
        if self._multi_index:
            msg = "Cannot remove a row from a table with a multi index"
            display(Javascript('alert("%s")' % msg))
            return
        self.send({'type': 'remove_row'})

    def get_data_and_call_function(self, value=None):
        self.send({'type': 'request_row_data'})

    def get_filters(self, value=None):
        self.send({'type': 'get_filters'})

    def update_grade(self, algo_id, grader, grade):
        row_ix = self.df[self.df.algo_id == algo_id].index.values[0]
        col_ix = self.df.columns.get_loc(grader)
        msg = {
            'type': 'grade_cell_updated',
            'row_ix': row_ix,
            'col_ix': col_ix,
            'new_val': grade,
        }
        self.send(msg)

    def _handle_qgrid_msg(self, widget, content, buffers=None):
        """Handle incoming messages from the QGridView"""
        if 'type' not in content:
            return
        if content['type'] == 'remove_row':
            self.df.drop(content['row'], inplace=True)

        elif content['type'] == 'cell_change':
            try:
                self.df.set_value(self.df.index[content['row']],
                                  content['column'], content['value'])
            except ValueError:
                pass
        elif content['type'] == 'row_data':
            row_data = content['data']
            # display(self.user_function(row_data))
            return row_data

        elif content['type'] == 'get_filters':
            self.apply_filters_to_data(content['data'])
            print content['data']

        elif content['type'] == 'selected_row_change':
            row_data = content['data']
            self.selected_id = row_data['algo_id']
            self.selected_row = row_data


    # eventually, we can send min and max values to the slider view
    # by updating

    def apply_filters_to_data(self, filters):
        for filt in filters:
            col = filt['column']['field']
            print filt.keys()
            print filt
            if 'slider_elem' in filt.keys():
                min_val = filt.get('filter_value_min')
                if min_val is not None:
                    self.bz_data = self.bz_data[self.bz_data[col] > float(min_val)][0:]

                max_val = filt.get('filter_value_max')
                if max_val is not None:
                    self.bz_data = self.bz_data[self.bz_data[col] < float(max_val)][0:]
            

        self.update_view_after_filter()

    def update_view_after_filter(self):

        # trigger an update of the df json
        self._bz_data_changed()
        self.remote_js = True
        div_id = str(uuid.uuid4())
        grid_options = json.loads(self.grid_options)
        grid_options['editable'] = False

        raw_html = SLICK_GRID_CSS.format(
            div_id=div_id,
            cdn_base_url=self._cdn_base_url,
        )
        raw_js = SLICK_GRID_JS.format(
            cdn_base_url=self._cdn_base_url,
            div_id=div_id,
            data_frame_json=self._df_json,
            column_types_json=self._column_types_json,
            options_json=json.dumps(grid_options),
        )
        clear_output()
        display_html(raw_html, raw=True)
        display_javascript(raw_js, raw=True)


    def export(self, value=None):
        # trigger an update of the df json
        self._bz_data_changed()
        self.remote_js = True
        div_id = str(uuid.uuid4())
        grid_options = json.loads(self.grid_options)
        grid_options['editable'] = False

        raw_html = SLICK_GRID_CSS.format(
            div_id=div_id,
            cdn_base_url=self._cdn_base_url,
        )
        raw_js = SLICK_GRID_JS.format(
            cdn_base_url=self._cdn_base_url,
            div_id=div_id,
            data_frame_json=self._df_json,
            column_types_json=self._column_types_json,
            options_json=json.dumps(grid_options),
        )

        display_html(raw_html, raw=True)
        display_javascript(raw_js, raw=True)
