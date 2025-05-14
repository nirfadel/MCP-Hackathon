import { Component } from '@angular/core';
import { AddressService } from '../../services/address.service';

interface ChatMessage {
  text: string;
  isUser: boolean;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss'],
  standalone: false
})
export class ChatComponent {
  messages: ChatMessage[] = [];
  addressInput: string = '';

  constructor(private addressService: AddressService) {}

  searchAddress(): void {
    if (!this.addressInput.trim()) return;

    // Add user message
    this.messages.push({
      text: this.addressInput,
      isUser: true
    });

    // Call service
    this.addressService.searchAddress(this.addressInput)
      .subscribe({
        next: (response) => {
          this.messages.push({
            text: 'Here is your address information.',
            isUser: false
          });
          // Handle PDF display if needed
        },
        error: (error) => {
          this.messages.push({
            text: 'Sorry, there was an error processing your request.',
            isUser: false
          });
        }
      });

    this.addressInput = '';
  }
}