"use client";

import { useState } from "react";
import Link from "next/link";

function isSafeDownloadUrl(url: string | undefined): url is string {
  if (!url) return false;
  const trimmed = url.trim();
  if (!trimmed) return false;
  return (
    trimmed.startsWith("https://") ||
    trimmed.startsWith("http://") ||
    trimmed.startsWith("/")
  );
}

function AndroidLogo() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M17.523 15.341a.999.999 0 1 1 0-1.998.999.999 0 0 1 0 1.998m-11.046 0a.999.999 0 1 1 0-1.998.999.999 0 0 1 0 1.998m11.405-6.02l1.997-3.46a.416.416 0 0 0-.152-.567.416.416 0 0 0-.568.152l-2.022 3.503C15.63 8.263 13.88 7.88 12 7.88s-3.63.383-5.137 1.069L4.841 5.446a.416.416 0 0 0-.568-.152.416.416 0 0 0-.152.567l1.997 3.46C2.688 11.186.343 14.658 0 18.761h24c-.343-4.103-2.688-7.575-6.118-9.44" />
    </svg>
  );
}

function WindowsLogo() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M2 3.5L10.8 2.2v9.1H2V3.5zm9.9-1.4L22 .6v10.7H11.9V2.1zM2 12.6h8.8v9.2L2 20.5v-7.9zm9.9 0H22v10.8l-10.1-1.5v-9.3z" />
    </svg>
  );
}

export function HeroDownloadCta() {
  const androidUrl =
    process.env.NEXT_PUBLIC_ANDROID_DOWNLOAD_URL || "/downloads/MediLocker-release.apk";
  const windowsUrl =
    process.env.NEXT_PUBLIC_WINDOWS_DOWNLOAD_URL || "/downloads/MediLocker-Setup-x64.exe";
  const hasAndroid = isSafeDownloadUrl(androidUrl);
  const hasWindows = isSafeDownloadUrl(windowsUrl);

  const [notice, setNotice] = useState<string>("");

  const baseBtnClass =
    "h-12 w-full px-5 rounded-full text-[13.5px] font-medium inline-flex items-center justify-center gap-2.5 whitespace-nowrap transition-all active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#090909] focus-visible:ring-offset-2";

  return (
    <div className="w-full md:w-[440px] shrink-0">
      {/* Row 1: Two equal-width download buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
        {hasAndroid ? (
          <a
            href={androidUrl.trim()}
            download
            type="application/vnd.android.package-archive"
            className={`${baseBtnClass} bg-[#090909] text-white border border-[#090909] hover:bg-[#222222]`}
          >
            <AndroidLogo />
            <span>Download for Android</span>
          </a>
        ) : (
          <button
            type="button"
            onClick={() =>
              setNotice(
                "Android APK release is not published yet. Set NEXT_PUBLIC_ANDROID_DOWNLOAD_URL to enable download."
              )
            }
            aria-label="Download for Android (release artifact not yet published)"
            className={`${baseBtnClass} bg-[#090909] text-white border border-[#090909] hover:bg-[#222222]`}
          >
            <AndroidLogo />
            <span>Download for Android</span>
          </button>
        )}

        {hasWindows ? (
          <a
            href={windowsUrl.trim()}
            download
            className={`${baseBtnClass} bg-white text-[#090909] border border-[#090909] hover:bg-[#E6E6E6]`}
          >
            <WindowsLogo />
            <span>Download for Windows</span>
          </a>
        ) : (
          <button
            type="button"
            onClick={() =>
              setNotice(
                "Windows installer release is not published yet. Set NEXT_PUBLIC_WINDOWS_DOWNLOAD_URL to enable download."
              )
            }
            aria-label="Download for Windows (release artifact not yet published)"
            className={`${baseBtnClass} bg-white text-[#090909] border border-[#090909] hover:bg-[#E6E6E6]`}
          >
            <WindowsLogo />
            <span>Download for Windows</span>
          </button>
        )}
      </div>

      {/* Row 2: Full-width Get Started Free button */}
      <div className="mt-3 w-full">
        <Link
          href="/dashboard"
          className={`${baseBtnClass} bg-[#090909] text-white border border-[#090909] hover:bg-[#222222]`}
        >
          <span>Get Started Free</span>
        </Link>
      </div>

      {notice && (
        <p
          role="status"
          aria-live="polite"
          className="mt-2.5 text-[12px] text-[#555555] leading-snug"
        >
          {notice}
        </p>
      )}
    </div>
  );
}
