import Foundation

/// A small SwiftPM program exercising Red's official Swift language pack.
protocol Greeter {
    associatedtype Message

    func greet(_ name: String) async -> Message
}

struct FriendlyGreeter: Greeter {
    let prefix: String

    func greet(_ name: String) async -> String {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        return "\(prefix), \(trimmed)!"
    }
}

@main
enum RedSwiftExample {
    static func main() async {
        let greeter = FriendlyGreeter(prefix: "Hello from Red")
        print(await greeter.greet("Swift"))
    }
}
