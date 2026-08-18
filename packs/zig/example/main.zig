// A representative Zig source file for Red's grammar checks.
const std = @import("std");

const DEFAULT_GREETING: []const u8 = "Hello";

const Greeter = struct {
    prefix: []const u8,

    pub fn greet(self: *const Greeter, name: []const u8) void {
        const message = "{s}, {s}! {d}\n";
        std.debug.print(message, .{ self.prefix, name, 42 });
        _ = undefined;
    }
};

pub fn main() void {
    var greeter = Greeter{ .prefix = DEFAULT_GREETING };
    greeter.greet("Red");
}
