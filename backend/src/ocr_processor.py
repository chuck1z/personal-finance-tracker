import pytesseract
from pytesseract import TesseractError
from PIL import Image
import pdf2image
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
import re
import pandas as pd
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info("Converted %d pages from PDF %s", len(images), pdf_path)
            return images
        except (PDFInfoNotInstalledError, PDFPageCountError, FileNotFoundError) as e:
            logger.error("Error converting PDF %s: %s", pdf_path, e)
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
        except (TesseractError, OSError) as e:
            logger.error("Error during OCR: %s", e)
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
                logger.info("Processing page %d", i + 1)
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
            logger.info("Transactions saved to %s", csv_filename)
            result['csv_file'] = csv_filename

        return result

# Example usage
if __name__ == "__main__":
    ocr = BankStatementOCR()
    statement_path = "bank_statement.pdf"  # Change to your file path

    if os.path.exists(statement_path):
        logger.info("Processing %s...", statement_path)
        result = ocr.process_statement(statement_path)
        logger.info(result)
    else:
        logger.error("Statement file not found")

