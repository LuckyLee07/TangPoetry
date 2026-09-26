import SwiftUI

@main
struct TangPoetryApp: App {
    @StateObject private var store = PoemStore()
    var body: some Scene {
        WindowGroup {
            ReaderView().environmentObject(store)
                .tint(Color(red: 0.63, green: 0.23, blue: 0.15))
                .preferredColorScheme(.light)
        }
    }
}
