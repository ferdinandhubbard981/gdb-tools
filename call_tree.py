import gdb
from treelib import Tree

class CallTreeCommand(gdb.Command):
    """Generates a call tree up to a specified depth by stepping into calls.

    Usage:
        call-tree --depth N
    """

    def __init__(self):
        super(CallTreeCommand, self).__init__("call-tree", gdb.COMMAND_USER)
        self.max_depth = 2
        self.call_tree = Tree()  # Use treelib.Tree to store the tree structure
        self.current_depth = 0
        self.done = False
        self.initial_frame = None  # Store the initial frame for depth calculation
        self.node_counter = 0  # Counter to generate unique node IDs
        self.current_parent = None  # Track the current parent node

    def invoke(self, arg, from_tty):
        """Parses arguments and starts the process."""
        # Parse depth argument
        args = arg.split()
        if len(args) == 2 and args[0] == "--depth":
            try:
                self.max_depth = int(args[1])
            except ValueError:
                print("Error: Depth must be an integer.")
                return

        # Reset state
        self.call_tree = Tree()
        self.current_depth = 0
        self.done = False
        self.node_counter = 0
        self.current_parent = None

        # Store the initial frame
        self.initial_frame = gdb.newest_frame()
        if not self.initial_frame:
            print("Error: no initial frame")
            return

        # Add the root node (initial function)
        initial_function = self.initial_frame.name()
        root_node_id = "root"
        self.call_tree.create_node(initial_function, root_node_id)  # Root node with ID "root"
        self.current_parent = root_node_id  # Set the root node as the initial parent

        # Hook stop event
        gdb.events.stop.connect(self.stop_handler)

        # Start stepping
        gdb.execute("step")

    def stop_handler(self, event):
        """Handles breakpoints and function calls."""
        if self.done:
            return

        frame = gdb.newest_frame()
        if not frame:
            print("Error: no frame")
            return

        # Calculate the depth relative to the initial frame
        temp_frame = frame
        previous_depth = self.current_depth
        self.current_depth = 0
        while temp_frame and temp_frame != self.initial_frame:
            self.current_depth += 1
            temp_frame = temp_frame.older()

        function_name = frame.name()
        print(f"current function: {function_name}")
        print(f"current depth: {self.current_depth}")

        # we know that we are not at max depth, because if we were we would have stepped out to a lower depth
        if self.current_depth == previous_depth:
            gdb.execute("step")

        # Add the current function to the tree
        if self.current_depth == 0:
            # We are back at the root node
            # Stop execution if we have returned back to the initial function
            self.done = True
            gdb.events.stop.disconnect(self.stop_handler)
            self.print_tree()
        elif self.current_depth > previous_depth:
            # We stepped into a new function
            node_id = f"node_{self.node_counter}"
            self.node_counter += 1
            self.call_tree.create_node(function_name, node_id, parent=self.current_parent)
            self.current_parent = node_id  # Update the current parent
        elif self.current_depth < previous_depth:
            # We stepped out of a function
            # Find the parent node by moving up the tree
            parent_node = self.call_tree.parent(self.current_parent)
            if parent_node:
                self.current_parent = parent_node.identifier

        # decide what to do (step in or out)
        if self.current_depth == 0:
            pass
        elif self.current_depth < self.max_depth:
            # Step into the next function call
            gdb.execute("step")
        else:
            # We are at max depth OR returning from a function
            gdb.execute("finish")

    def print_tree(self):
        """Formats and prints the call tree."""
        print("\nCall Tree:")
        self.call_tree.show()
        self.call_tree.save2file("tree.txt")  # Save the tree to a file

# Register command
CallTreeCommand()