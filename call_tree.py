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

        # Store the initial frame
        self.initial_frame = gdb.newest_frame()
        if not self.initial_frame:
            print("Error: no initial frame")
            return

        # Add the root node (initial function)
        initial_function = self.initial_frame.name()
        self.call_tree.create_node(initial_function, "root")  # Root node with ID "root"

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
        if self.current_depth == 0 or self.current_depth < previous_depth:
            # This is the root node, which is already added or we moved up to a previous function which was also already added
            pass
        else:
            # Generate a unique node ID
            node_id = f"node_{self.node_counter}"
            self.node_counter += 1

            # Find the parent node ID
            parent_frame = frame.older()
            if parent_frame:
                parent_function = parent_frame.name()
                parent_node = self.call_tree.get_node(self._find_node_id_by_name(parent_function))
                if parent_node:
                    self.call_tree.create_node(function_name, node_id, parent=parent_node.identifier)

        # Stop execution if we have returned back to the initial function
        if self.current_depth == 0:
            self.done = True
            gdb.events.stop.disconnect(self.stop_handler)
            self.print_tree()

        elif self.current_depth < self.max_depth:
            # Step into the next function call
            gdb.execute("step")
        else:
            # We are at max depth OR returning from a function
            gdb.execute("finish")

    def _find_node_id_by_name(self, name):
        """Helper function to find a node's ID by its name."""
        for node in self.call_tree.all_nodes():
            if node.tag == name:
                return node.identifier
        return None

    def print_tree(self):
        """Formats and prints the call tree."""
        print("\nCall Tree:")
        self.call_tree.show()
        self.call_tree.save2file("tree.txt")

# Register command
CallTreeCommand()