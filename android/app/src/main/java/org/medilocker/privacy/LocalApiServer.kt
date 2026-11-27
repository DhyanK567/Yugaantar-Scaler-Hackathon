package org.medilocker.privacy

import android.content.Context
import android.util.Base64
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import fi.iki.elonen.NanoHTTPD
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.security.SecureRandom

class LocalApiServer(
    private val context: Context,
    port: Int = 8000
) : NanoHTTPD("127.0.0.1", port) {

    init {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context))
        }
        val secret = getOrCreateDeviceSecret(context)
        val py = Python.getInstance()
        val bridge = py.getModule("android_api_bridge")
        bridge.callAttr("init_android_runtime", context.filesDir.absolutePath, secret)
    }

    private fun getOrCreateDeviceSecret(ctx: Context): String {
        val prefs = ctx.getSharedPreferences("medilocker_keystore_prefs", Context.MODE_PRIVATE)
        val existing = prefs.getString("raksha_local_secret", null)
        if (!existing.isNullOrBlank()) return existing
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        val generated = Base64.encodeToString(bytes, Base64.NO_WRAP)
        prefs.edit().putString("raksha_local_secret", generated).apply()
        return generated
    }

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri ?: "/"
        if (uri.startsWith("/api/")) {
            return handleApi(session, uri)
        }
        return serveStaticAsset(uri)
    }

    private fun handleApi(session: IHTTPSession, uri: String): Response {
        return try {
            val bodyMap = HashMap<String, String>()
            val bodyBytes: ByteArray = if (session.method == Method.POST || session.method == Method.PUT || session.method == Method.PATCH) {
                val len = session.headers["content-length"]?.toIntOrNull() ?: 0
                if (len > 0) {
                    val buf = ByteArray(len)
                    var read = 0
                    while (read < len) {
                        val r = session.inputStream.read(buf, read, len - read)
                        if (r <= 0) break
                        read += r
                    }
                    buf.copyOf(read)
                } else ByteArray(0)
            } else ByteArray(0)

            val headersJson = JSONObject(session.headers as Map<*, *>).toString()
            val bodyB64 = Base64.encodeToString(bodyBytes, Base64.NO_WRAP)
            val py = Python.getInstance()
            val bridge = py.getModule("android_api_bridge")
            val resultObj = bridge.callAttr(
                "handle_request",
                session.method.name,
                uri,
                session.queryParameterString ?: "",
                headersJson,
                bodyB64
            )
            val pyMap = resultObj.asMap()
            val statusCode = pyMap[py.builtins.callAttr("str", "status")]?.toInt() ?: 200
            val ct = pyMap[py.builtins.callAttr("str", "content_type")]?.toString() ?: "application/json"
            val respB64 = pyMap[py.builtins.callAttr("str", "body_b64")]?.toString() ?: ""
            val respBytes = Base64.decode(respB64, Base64.DEFAULT)

            val status = Response.Status.lookup(statusCode) ?: Response.Status.OK
            val res = newFixedLengthResponse(status, ct, ByteArrayInputStream(respBytes), respBytes.size.toLong())
            val extraHeaders = pyMap[py.builtins.callAttr("str", "headers")]?.asMap()
            extraHeaders?.forEach { (k, v) ->
                res.addHeader(k.toString(), v.toString())
            }
            res
        } catch (e: Exception) {
            val errJson = JSONObject(mapOf("detail" to "Internal local engine error")).toString()
            newFixedLengthResponse(Response.Status.INTERNAL_ERROR, "application/json", errJson)
        }
    }

    private fun serveStaticAsset(rawUri: String): Response {
        if (rawUri.contains("..")) {
            return newFixedLengthResponse(Response.Status.BAD_REQUEST, "text/plain", "Invalid path")
        }
        val clean = rawUri.trimStart('/')
        val candidates = if (clean.isEmpty()) {
            listOf("www/index.html")
        } else {
            listOf("www/$clean", "www/$clean/index.html", "www/${clean.trimEnd('/')}/index.html")
        }
        for (assetPath in candidates) {
            try {
                val stream = context.assets.open(assetPath)
                val bytes = stream.readBytes()
                stream.close()
                return newFixedLengthResponse(Response.Status.OK, guessMime(assetPath), ByteArrayInputStream(bytes), bytes.size.toLong())
            } catch (_: Exception) {
            }
        }
        return try {
            val stream = context.assets.open("www/404.html")
            val bytes = stream.readBytes()
            stream.close()
            newFixedLengthResponse(Response.Status.NOT_FOUND, "text/html; charset=utf-8", ByteArrayInputStream(bytes), bytes.size.toLong())
        } catch (_: Exception) {
            newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Not Found")
        }
    }

    private fun guessMime(path: String): String = when {
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
}
