# helpers.py
#
# Defines few utilities used throughout the code
################################################################################
import gtk
import gobject
import numpy as numarray
import os

CONFIG_FILE = "lib/config.ddscon"
        
################################################################################
# class typical_ncol_tree
#
# Generates a GTK tree (a table), with column header and data type determined
# by the passed arguments. For an example how it looks like, see any of my logics
################################################################################
class typical_ncol_tree:
    def __init__(self, tree_def):
	# Create a liststore to hold the data. 
	# Use tree_def = [(type, name, editable) ...] to determina data type
        self.model = gtk.ListStore(*map(lambda x:x[0], tree_def))
        self.rows = {}

	# Create a treeview
        self.treeview = gtk.TreeView(self.model)
        # Add all the columns
        for col in range(len(tree_def)):
            # New renderer for the column
            renderer = gtk.CellRendererText()
            (type, name, c_edit) = tree_def[col]
            # should the column be editable?
            if (c_edit > 0):
                renderer.connect('edited', self.cell_edited_callback, col)
                renderer.set_property('editable', True)
            # If the cell is not float, render it as text
            if (type != gobject.TYPE_DOUBLE and type != gobject.TYPE_FLOAT): 
                self.treeview.insert_column_with_attributes(-1, name, renderer, text=col)
            # If the cell is float/double, use a custom renderer
            else:
                tvcol = gtk.TreeViewColumn(name, renderer)
                tvcol.set_cell_data_func(renderer, self.render_floats, col)
                self.treeview.append_column(tvcol)
    ###############################################################################
    # cell_edited_callback
    #
    # called anytime data is changed in the tree. Changes the data in
    # underlying model
    ###############################################################################
    def cell_edited_callback(self, cell, path, text, col=0):
        iter = self.model.get_iter(path)
        self.set_data_from_text(iter, col, text)
        return gtk.TRUE

    ##############################################################################
    # add_row
    #
    # add a row to the tree, the row_data tuple must match columns data types
    # saves a pointer to the new row in self.rows
    ##############################################################################
    def add_row(self, *row_data):
        iter = self.model.append(row=row_data)
        self.rows[row_data[0]] = iter
        return

    ##############################################################################
    # get_data
    #
    # Retrieve data from a specified row/column
    ##############################################################################
    def get_data(self, name, col):
	print "get_data"
        iter = self.rows[name]
        return self.model.get_value(iter, col)

    ##############################################################################
    # set_data
    #
    # Retrieve data from a specified row/column
    ##############################################################################
    def set_data(self, name, col, value):
        iter = self.rows[name]
        return self.model.set_value(iter, col, value)

    ##############################################################################
    # set_data_from_text
    #
    # Parses the text in a cell as an int, float or str, and changes the value in
    # underlying model
    #############################################################################
    def set_data_from_text(self, iter, col, text):
        type = self.model.get_column_type(col)
        try:
            if (type in [gobject.TYPE_INT, gobject.TYPE_UINT]):
                val = int(text)
            elif (type in [gobject.TYPE_DOUBLE, gobject.TYPE_FLOAT]):
                val = float(text)
            elif (type == gobject.TYPE_STRING):
                val = text
                if (col == 0):
                    name = self.model.get_value(iter, col)
                    self.rows.pop(name)
                    self.rows[text] = iter
                
            return self.model.set_value(iter, col, val)
        except:
            print "Invalid value passed to tree!"
        return

    #############################################################################
    # render_floats
    #
    # Converts a float to a text value, and updates the cell text
    #############################################################################
    def render_floats(self, column, cell, model, iter, col_no = None):
        value = model.get_value(iter, col_no)
        return cell.set_property('text', "%.8g"%value)

    #############################################################################
    # save_state
    #
    # saves all the values in the tree to a file using save_to_config
    #############################################################################
    def save_state(self, root):
        for key in self.rows:
            for col in range(1, self.model.get_n_columns()):
                save_to_config(root + ':tree:' + key + ':' + str(col), self.get_data(key, col))
        return

    #############################################################################
    # restore_state
    #
    # restores all the values from file using read_from_config
    #############################################################################
    def restore_state(self, root):
        for key in self.rows:
            iter = self.rows[key]
            for col in range(1, self.model.get_n_columns()):
                val = read_from_config(root + ':tree:' + key + ':' + str(col))
                if (val): self.set_data_from_text(iter, col, val)
        return

######################################################################
# save_to_config
#
# saves a value to a CONFIG_FILE file, under header root. It either
# updates the value, if such header is already present, or adds
# both the header and value
######################################################################
def save_to_config(root, value):
    if (os.access(CONFIG_FILE, os.F_OK) == 1):
        fd = file(CONFIG_FILE, "r+")
    else:
        fd = file(CONFIG_FILE, "w+")
    
    fd.seek(0,2)
    filesize = fd.tell()
    fd.seek(0,0)

    # Look for the header root
    start = 0
    for line in fd:
        if line.startswith(root):
            end = start + len(line)
            break
        start = start + len(line)
    else:
        start = filesize
        end = filesize

    fd.seek(end, 0)

    newtext = root + ":" + str(value) + '\n'
    # save all after the header root
    oldcontent = fd.read(filesize - end)
    fd.seek(start)
    # truncate the file at the header root
    fd.truncate(start)
    # Write new data, and rest of file
    # (effectively replacing old data with new)
    fd.write(newtext + oldcontent)
    fd.close()

################################################################
# read_from_config
#
# Reads the value saved under header root from CONFIG_FILE
################################################################
def read_from_config(root):
    if (os.access(CONFIG_FILE, os.F_OK) == 0): return
    fd = file(CONFIG_FILE, "r")
    for line in fd:
        if line.startswith(root + ':'):
            fd.close()
            return line[len(root + ':'):-1]

    fd.close()
    return

################################################################
# read_from_config
#
# Reads the value saved under header root from CONFIG_FILE
################################################################
def list_keys_from_config(root):
    if (os.access(CONFIG_FILE, os.F_OK) == 0): return
    fd = file(CONFIG_FILE, "r")
    rv = []
    for line in fd:
        if line.startswith(root + ':'):
            rv = rv + [line[len(root + ':'):-1].split(':')[0]]

    fd.close()
    return rv

