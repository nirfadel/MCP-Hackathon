import { Component, Input, OnInit } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-pdf-viewer',
  templateUrl: './pdf-viewer.component.html',
  styleUrls: ['./pdf-viewer.component.scss'],
  standalone: false
})
export class PdfViewerComponent implements OnInit {
  @Input() pdfPath: string | undefined;
  pdfSrc: SafeResourceUrl | undefined;

  constructor(private sanitizer: DomSanitizer) { }

  ngOnInit(): void {
    // Sanitize the PDF URL to make it safe for use in iframe
    if (this.pdfPath) {
      this.pdfSrc = this.sanitizer.bypassSecurityTrustResourceUrl(this.pdfPath);
    } else {
      this.pdfSrc = undefined;
    }
  }

  downloadPdf(): void {
    const link = document.createElement('a');
    link.href = this.pdfPath ?? '';
    link.download = 'generated-presentation.pptx';
    link.click();
  }
}