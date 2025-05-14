
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PdfService {
  private apiUrl = 'YOUR_API_ENDPOINT'; // Replace with your actual API endpoint

  constructor(private http: HttpClient) {}

  generatePdf(data: any): Observable<Blob> {
    return this.http.post<Blob>(`${this.apiUrl}/generate-pdf`, data, {
      responseType: 'blob' as 'json'
    });
  }

  downloadPdf(fileName: string): void {
    const link = document.createElement('a');
    link.href = `${this.apiUrl}/download/${fileName}`;
    link.download = fileName;
    link.click();
  }
}