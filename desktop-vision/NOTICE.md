# Notices

Created by lvren with GPT-6.1Sol.

The project source code and our self-trained ONNX weights are provided under the included MIT license, copyright 2026 lvren. Commercial use is permitted under that license. The project does not claim ownership of the game, third-party videos, fonts or runtime libraries.

The original probability engines are copied without modification from lvren's MIT-licensed GWYF strategy assistant v7.7.2. This prototype is separate from the stable website.

The models were trained from scratch with PyTorch; no third-party pretrained weights are included. The reviewed `nighthawk776/Gamble-with-your-Friends-Blackjack-Counter` code and models have not been copied into this kit. No FriendsAdvisor injection or private-state prediction code is used.

Research used public gameplay videos listed in DATA_SOURCES.md. Those videos retain their original rights. No video files or extracted game frames are included in the downloadable kit. Documentation of a public source is not a grant to redistribute that source under this project's MIT license.

Synthetic training glyphs use locally installed DejaVu fonts and Google Fonts: Kalam, Lilita One (SIL Open Font License) and Luckiest Guy (Apache License 2.0 at the referenced Google Fonts path). Fonts are not bundled. Their original license files and authorship remain available in their respective upstream directories.

The Windows portable package bundles the official embedded CPython 3.14.8 x64 runtime and binary runtime dependencies: NumPy (BSD), OpenCV (Apache 2.0), MSS (MIT), pywebview (BSD), and their dependencies. All bundled package dist-info/license files are preserved. Refer to those files for each component’s terms. Microsoft WebView2 and Python retain their own licenses. PyTorch, ONNX and Pillow are development tools, not included in the end-user portable package.

Version 0.2 uses OpenCV DNN for inference. ONNX Runtime is no longer a runtime requirement. Models were retrained with balanced data and an expanded architecture.

Version 0.3 includes Microsoft’s official Evergreen WebView2 x64 Standalone Installer, unmodified, for offline per-user preparation when WebView2 is missing. Microsoft’s own license and installation terms apply to that component; this project’s MIT license does not relicense it. Source URLs and SHA-256 checksums are preserved in runtime-support. The project does not install or change the user’s system Python.
