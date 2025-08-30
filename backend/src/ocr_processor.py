import pytesseract
from PIL import Image
import pdf2image
import re
import pandas as pd
from datetime import datetime
import os

class BankStatementOCR:
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the Bank Statement OCR processor
        
        Args:
            tesseract_cmd: Path to tesseract executable (if not in PATH)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def pdf_to_images(self, pdf_path, dpi=300):
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for conversion
        
        Returns:
            List of PIL Image objects
        """
        try:
            images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
            print(f"Converted {len(images)} pages from PDF")
            return images
        except Exception as e:
            print(f"Error converting PDF: {e}")
            return []
    
    def preprocess_image(self, image):
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image: PIL Image object
        
        Returns:
            Preprocessed PIL Image
        """
        # Convert to grayscale
        image = image.convert('L')
        
        # Optionally resize for better OCR
        width, height = image.size
        if width < 2000:
            new_width = 2000
            new_height = int(height * (new_width / width))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def extract_text(self, image):
        """
        Extract text from image using OCR
        
        Args:
            image: PIL Image object or path to image
        
        Returns:
            Extracted text string
        """
        try:
            # Preprocess if it's an image object
            if isinstance(image, Image.Image):
                image = self.preprocess_image(image)
            
            # OCR configuration for better accuracy
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text
        except Exception as e:
            print(f"Error during OCR: {e}")
            return ""
    
    def parse_transactions(self, text):
        """
        Parse transaction data from extracted text
        
        Args:
            text: OCR extracted text
        
        Returns:
            List of transaction dictionaries
        """
        transactions = []
        
        # Common patterns for transaction lines
        # Adjust these patterns based on your bank's statement format
        patterns = {
            'date_amount': r'(\d{2}[/-]\d{2}[/-]\d{2,4})\s+.*?\s+(\d+[,.]?\d*\.?\d{2})',
            'description': r'\d{2}[/-]\d{2}[/-]\d{2,4}\s+(.*?)\s+\d+[,.]?\d*\.?\d{2}',
            'balance': r'[Bb]alance.*?(\d+[,.]?\d*\.?\d{2})',
        }
        
        lines = text.split('\n')
        
        for line in lines:
            # Try to match transaction pattern
            date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{2,4})', line)
            amount_match = re.search(r'(\d+[,.]?\d*\.?\d{2})(?:\s|$)', line)
            
            if date_match and amount_match:
                transaction = {
                    'date': date_match.group(1),
                    'amount': amount_match.group(1).replace(',', ''),
                    'description': line.strip(),
                    'raw_line': line
                }
                
                # Try to extract description between date and amount
                desc_pattern = f"{re.escape(date_match.group(1))}\s+(.*?)\s+{re.escape(amount_match.group(1))}"
                desc_match = re.search(desc_pattern, line)
                if desc_match:
                    transaction['description'] = desc_match.group(1).strip()
                
                transactions.append(transaction)
        
        return transactions
    
    def extract_account_info(self, text):
        """
        Extract account information from the statement
        
        Args:
            text: OCR extracted text
        
        Returns:
            Dictionary with account information
        """
        info = {}
        
        # Pattern matching for common account info
        patterns = {
            'account_number': r'[Aa]ccount\s*[Nn]o\.?\s*:?\s*(\d+)',
            'statement_period': r'[Ss]tatement\s*[Pp]eriod\s*:?\s*(.*?to.*?\d{4})',
            'opening_balance': r'[Oo]pening\s*[Bb]alance\s*:?\s*(\d+[,.]?\d*\.?\d{2})',
            'closing_balance': r'[Cc]losing\s*[Bb]alance\s*:?\s*(\d+[,.]?\d*\.?\d{2})',
            'customer_name': r'[Nn]ame\s*:?\s*([A-Z][A-Za-z\s]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info[key] = match.group(1).strip()
        
        return info
    
    def process_statement(self, file_path, output_format='dataframe'):
        """
        Process a complete bank statement
        
        Args:
            file_path: Path to the statement file (PDF or image)
            output_format: 'dataframe', 'dict', or 'csv'
        
        Returns:
            Processed data in specified format
        """
        all_text = ""
        all_transactions = []
        
        # Check if it's a PDF or image
        if file_path.lower().endswith('.pdf'):
            images = self.pdf_to_images(file_path)
            for i, image in enumerate(images):
                print(f"Processing page {i+1}...")
                text = self.extract_text(image)
                all_text += text + "\n"
                transactions = self.parse_transactions(text)
                all_transactions.extend(transactions)
        else:
            # Process as image
            image = Image.open(file_path)
            all_text = self.extract_text(image)
            all_transactions = self.parse_transactions(all_text)
        
        # Extract account info from first page
        account_info = self.extract_account_info(all_text)
        
        # Format output
        result = {
            'account_info': account_info,
            'transactions': all_transactions,
            'raw_text': all_text
        }
        
        if output_format == 'dataframe' and all_transactions:
            df = pd.DataFrame(all_transactions)
            result['dataframe'] = df
        elif output_format == 'csv' and all_transactions:
            df = pd.DataFrame(all_transactions)
            csv_filename = file_path.rsplit('.', 1)[0] + '_transactions.csv'
            df.to_csv(csv_filename, index=False)
            print(f"Transactions saved to {csv_filename}")
            result['csv_file'] = csv_filename
        
        return result

# Example usage
if __name__ == "__main__":
    # Initialize the OCR processor
    # Uncomment and set path if tesseract is not in PATH
    # ocr = BankStatementOCR(tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    ocr = BankStatementOCR()
    
    # Process a bank statement
    statement_path = "bank_statement.pdf"  # Change to your file path
    
    if os.path.exists(statement_path):
        print(f"Processing {statement_path}...")
        result = ocr.process_statement