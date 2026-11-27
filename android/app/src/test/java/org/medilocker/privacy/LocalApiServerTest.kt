package org.medilocker.privacy

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalApiServerTest {

    @Test
    fun loopbackHostCheckAllowsOnlyLocalhost() {
        assertTrue(isAllowedLocalHost("127.0.0.1"))
        assertTrue(isAllowedLocalHost("localhost"))
        assertFalse(isAllowedLocalHost("example.com"))
        assertFalse(isAllowedLocalHost("192.168.1.10"))
        assertFalse(isAllowedLocalHost(null))
    }

    @Test
    fun mimeTypeMappingCoversNextAssetsAndDownloads() {
        assertEquals("text/html; charset=utf-8", guessStaticMime("www/index.html"))
        assertEquals("application/javascript; charset=utf-8", guessStaticMime("www/_next/static/chunks/app.js"))
        assertEquals("text/css; charset=utf-8", guessStaticMime("www/_next/static/chunks/app.css"))
        assertEquals("application/json; charset=utf-8", guessStaticMime("www/manifest.json"))
        assertEquals("image/svg+xml", guessStaticMime("www/next.svg"))
        assertEquals("font/woff2", guessStaticMime("www/font.woff2"))
    }

    @Test
    fun staticCandidatesPreventTraversalAndMapCleanRoutes() {
        val rootCandidates = buildStaticCandidates("/")
        assertEquals(listOf("www/index.html"), rootCandidates)

        val dashCandidates = buildStaticCandidates("/dashboard/")
        assertEquals(
            listOf("www/dashboard/", "www/dashboard//index.html", "www/dashboard/index.html"),
            dashCandidates
        )

        val traversalCandidates = buildStaticCandidates("/../../etc/passwd")
        assertTrue(traversalCandidates.isEmpty())
    }

    private fun isAllowedLocalHost(host: String?): Boolean =
        host == "127.0.0.1" || host == "localhost"

    private fun guessStaticMime(path: String): String = when {
        path.endsWith(".html") -> "text/html; charset=utf-8"
        path.endsWith(".js") -> "application/javascript; charset=utf-8"
        path.endsWith(".css") -> "text/css; charset=utf-8"
        path.endsWith(".json") -> "application/json; charset=utf-8"
        path.endsWith(".jpg") || path.endsWith(".jpeg") -> "image/jpeg"
        path.endsWith(".png") -> "image/png"
        path.endsWith(".svg") -> "image/svg+xml"
        path.endsWith(".ico") -> "image/x-icon"
        path.endsWith(".woff2") -> "font/woff2"
        else -> "application/octet-stream"
    }

    private fun buildStaticCandidates(rawUri: String): List<String> {
        if (rawUri.contains("..")) return emptyList()
        val clean = rawUri.trimStart('/')
        return if (clean.isEmpty()) {
            listOf("www/index.html")
        } else {
            listOf("www/$clean", "www/$clean/index.html", "www/${clean.trimEnd('/')}/index.html")
        }
    }
}
