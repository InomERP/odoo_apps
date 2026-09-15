# Third-party libraries bundled with this module

These are unmodified upstream builds, shipped so the PDF annotator works on a
server with no outbound internet access. Each folder keeps the library's own
licence file alongside the build.

| Library | Version | Licence | Used for |
|---|---|---|---|
| [PDF.js](https://mozilla.github.io/pdf.js/) | 3.11.174 | Apache-2.0 (`pdfjs/LICENSE`) | Rendering PDF pages in the annotator |
| [jsPDF](https://github.com/parallax/jsPDF) | 2.5.1 | MIT (`jspdf/LICENSE`) | Exporting the annotated document as a PDF |
| [html2canvas](https://html2canvas.hertzen.com/) | 1.4.1 | MIT (`html2canvas/LICENSE`) | Rasterising annotated pages for the export |

The loader in `static/src/js/pdf_annotator.js` requests these local copies
first and only falls back to the public CDN if a bundled file cannot be
served.
