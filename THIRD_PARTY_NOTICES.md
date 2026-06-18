# Third-party notices

This file is an engineering inventory for release packaging. A release build must regenerate and verify the inventory against the files it actually ships.

| Component | Purpose | License / distribution boundary |
| --- | --- | --- |
| PySide6 / Qt for Python | Windows desktop UI | LGPL-3.0-only, GPL-3.0-only, or commercial Qt terms. Release packaging must preserve notices and use replaceable Qt shared libraries when relying on LGPL terms. |
| PyInstaller | Windows executable packaging | GPL-2.0-or-later with the PyInstaller bootloader exception. The exception permits distribution of packaged applications. |
| Tesseract OCR | Optional OCR runtime | Apache-2.0. Language data attribution must be retained. |
| Unbabel COMET | Optional translation evaluator | Apache-2.0. The selected model is listed in MODEL_LICENSES.md. |
| Hugging Face Transformers | Local model runtime | Apache-2.0. Individual models have separate licenses. |
| PyTorch | Local model runtime | BSD-3-Clause. |
| Streamlit | Legacy validation UI | Apache-2.0. Not required by the final Qt runtime unless explicitly packaged. |
| Requests | HTTP client | Apache-2.0. |
| python-docx | DOCX input | MIT. |
| RapidFuzz | Text similarity | MIT. |
| SentencePiece | Tokenization | Apache-2.0. |
| Inno Setup | Windows installer compiler | Inno Setup License; commercial use and redistribution are permitted under its terms. The compiler is a build tool and is not installed with the application. |

Textractor, LunaTranslator, and GalTransl are interoperability references. Their source code and binaries are not bundled by default. Connecting through files, clipboard text, or documented local interfaces does not copy their implementations.

This inventory is not legal advice. Distributors remain responsible for validating the exact dependencies, models, notices, and obligations in each published artifact.
