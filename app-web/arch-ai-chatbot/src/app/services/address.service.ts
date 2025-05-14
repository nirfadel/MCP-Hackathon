
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Address } from '../models/address.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AddressService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  searchAddress(address: string): Observable<Address> {
    return this.http.post<Address>(`${this.apiUrl}/search`, { address });
  }
}