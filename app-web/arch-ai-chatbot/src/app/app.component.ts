import { Component } from '@angular/core';
import { AddressService } from './services/address.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  standalone: false
})
export class AppComponent {
  address: string = '';
  pptxPath: string | null = null;
  loading: boolean = false;
  error: string | null = null;

  constructor(private addressService: AddressService) {}

  async searchAddress() {
    if (!this.address.trim()) return;

    this.loading = true;
    this.error = null;
    this.pptxPath = null;

    try {
      const response = await this.addressService.searchAddress(this.address).toPromise();
      this.pptxPath = response && response.pptxPath ? response.pptxPath : null;
    } catch (err) {
      this.error = 'Error processing address. Please try again.';
      console.error(err);
    } finally {
      this.loading = false;
    }
  }
}