package org.medilocker.privacy

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var localServer: LocalApiServer? = null
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris ->
        fileUploadCallback?.onReceiveValue(uris.toTypedArray())
        fileUploadCallback = null
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = true
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.useWideViewPort = true
            settings.loadWithOverviewMode = true

            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    val host = request?.url?.host ?: return false
                    return host != "127.0.0.1" && host != "localhost"
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    webView: WebView?,
                    filePathCallback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?
                ): Boolean {
                    fileUploadCallback?.onReceiveValue(null)
                    fileUploadCallback = filePathCallback
                    filePickerLauncher.launch(arrayOf("*/*"))
                    return true
                }
            }

            setDownloadListener { url, _, _, _, _ ->
                if (url.startsWith("http://127.0.0.1:8000")) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                }
            }
        }

        setContentView(webView)
        webView.loadDataWithBaseURL(
            null,
            "<html><body style='margin:0;display:flex;align-items:center;justify-content:center;height:100vh;background:#F4F4F2;font-family:sans-serif;color:#111'><div style='text-align:center'><h2>MediLocker</h2><p>Initializing offline privacy engine...</p></div></body></html>",
            "text/html",
            "utf-8",
            null
        )

        Thread {
            val server = LocalApiServer(applicationContext, 8000).apply {
                start()
            }
            localServer = server
            runOnUiThread {
                if (!isFinishing && !isDestroyed) {
                    webView.loadUrl("http://127.0.0.1:8000/dashboard/")
                }
            }
        }.start()

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    finish()
                }
            }
        })
    }

    override fun onDestroy() {
        localServer?.stop()
        super.onDestroy()
    }
}
