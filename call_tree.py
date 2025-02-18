import gdb

class CallTreeCommand(gdb.Command):
    """Generates a call tree up to a specified depth by stepping into calls.

    Usage:
        call-tree --depth N
    """

    def __init__(self):
        super(CallTreeCommand, self).__init__("call-tree", gdb.COMMAND_USER)
        self.max_depth = 2
        self.call_tree = {}  # Dictionary to store the tree structure
        self.current_depth = 0
        self.done = False
        self.initial_frame = None  # Store the initial frame for depth calculation

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
        self.call_tree = {}
        self.current_depth = 0
        self.done = False

        # Store the initial frame
        self.initial_frame = gdb.newest_frame()
        if not self.initial_frame:
            print("Error: no initial frame")
            return

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
        
        # we know that we are not at max depth, because if we were we would have stepped out to a lower depth
        if self.current_depth == previous_depth:
            gdb.execute("step")

        function_name = frame.name()
        print(f"current function: {function_name}")
        print(f"current depth: {self.current_depth}")

        # Add to call tree
        if self.current_depth not in self.call_tree:
            self.call_tree[self.current_depth] = []
        self.call_tree[self.current_depth].append(function_name)

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


    def print_tree(self):
        """Formats and prints the call tree."""
        print("\nCall Tree:")
        for depth in sorted(self.call_tree.keys()):
            for function in self.call_tree[depth]:
                print("\t" * depth + function)

# Register command
CallTreeCommand()