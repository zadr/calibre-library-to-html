//
//  ContentView.swift
//  Books
//
//  Created by z on 8/17/25.
//

import SwiftUI
import WebKit

struct ContentView: View {
    var body: some View {
        if let url = Bundle.main.url(forResource: "books", withExtension: "html") {
            WebView(url: url)
                .ignoresSafeArea()
        } else {
            Text("books.html not found")
        }
    }
}

#Preview {
    ContentView()
}
