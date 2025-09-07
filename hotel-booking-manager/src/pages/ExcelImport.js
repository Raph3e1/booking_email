import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import * as XLSX from 'xlsx';

const ExcelImport = ({ showSnackbar }) => {
  const [file, setFile] = useState(null);
  const [previewData, setPreviewData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [listingName, setListingName] = useState('');

  // Define the column mapping
  const columnMapping = {
    'Book Number': 'Book Number',
    'Listing Name': 'listing_name',
    'Guest Name': 'Guest Name(s)',
    'Check-in': 'Check-in',
    'Check-in Time': 'check_in_time',
    'Check-out': 'Check-out',
    'Booked On': 'Booked on',
    'People': 'People',
    'Price': 'Price',
    'Unit Type': 'Unit type',
    'Phone Number': 'Phone number',
    'Payment Type': 'Payment method (payment provider)',
    'Commission': 'Commission %',
    'OTA': 'Booking',
    'Commission Amount': 'Commission Amount',
    'Status': 'Status'
  };

  const calculateCommissionAmount = (price, commissionPercent) => {
    if (!price || !commissionPercent) return '';
    const priceNum = parseFloat(price.toString().replace(/[^0-9.-]+/g, ''));
    const commissionNum = parseFloat(commissionPercent.toString().replace(/[^0-9.-]+/g, ''));
    if (isNaN(priceNum) || isNaN(commissionNum)) return '';
    return ((priceNum * commissionNum) / 100).toFixed(2);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Reset preview data when new file is selected
      setPreviewData([]);
      setFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
          
          // Get headers and first 100 rows for preview
          const excelHeaders = jsonData[0];
          const previewRows = jsonData.slice(1, 6);

          // Create a mapping of Excel headers to their indices
          const headerIndices = {};
          excelHeaders.forEach((header, index) => {
            headerIndices[header] = index;
          });

          // Create preview data with only the columns we want
          const previewHeaders = Object.keys(columnMapping);
          const mappedRows = previewRows.map(row => {
            const newRow = {};
            previewHeaders.forEach(header => {
              const excelHeader = columnMapping[header];
              const index = headerIndices[excelHeader];
              if (header === 'Commission Amount') {
                const price = index !== undefined ? row[headerIndices['Price']] : '';
                const commission = index !== undefined ? row[headerIndices['Commission %']] : '';
                newRow[header] = calculateCommissionAmount(price, commission);
              } else if (header === 'OTA') {
                // Set default value 'Booking' for OTA if not present
                newRow[header] = index !== undefined && row[index] ? row[index] : 'Booking';
              } else if (header === 'Listing Name') {
                // Use the entered listing name
                newRow[header] = listingName;
              } else if (header === 'Payment Type') {
                // Set default value 'OTA Collect' for Payment Type if not present
                newRow[header] = index !== undefined && row[index] ? row[index] : 'OTA Collect';
              } else if (header === 'Status') {
                // Convert status to CONFIRMED or CANCELLED
                const status = index !== undefined ? row[index] : '';
                newRow[header] = status.toString().toLowerCase() === 'ok' ? 'CONFIRMED' : 'CANCELLED';
              } else {
                newRow[header] = index !== undefined ? row[index] : '';
              }
            });
            return newRow;
          });

          setPreviewData({ headers: previewHeaders, rows: mappedRows });
        } catch (error) {
          showSnackbar('Error reading Excel file', 'error');
          setFile(null);
          setPreviewData([]);
        }
      };
      reader.readAsArrayBuffer(file);
    }
  };

  const handleSubmit = async () => {
    if (!file || !listingName) {
      showSnackbar('Please select a file and enter listing name', 'error');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('listing_name', listingName);

      const response = await fetch('http://localhost:8000/api/import-excel', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to import data');
      }

      showSnackbar('Data imported successfully', 'success');
      setFile(null);
      setPreviewData([]);
      setListingName('');
      window.location.reload();
    } catch (error) {
      showSnackbar(error.message || 'Error importing data', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 3 }}>
        Import Excel Data
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 3 }}>
          <TextField
            label="Listing Name"
            value={listingName}
            onChange={(e) => setListingName(e.target.value)}
            fullWidth
            required
          />
          <Button
            variant="contained"
            component="label"
            startIcon={<CloudUploadIcon />}
            disabled={loading}
          >
            Upload Excel File
            <input
              type="file"
              hidden
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
            />
          </Button>
        </Box>

        {previewData.headers && (
          <>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Preview (First 5 rows)
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f0f0f0', fontWeight: 'bold' }}>
                    {previewData.headers.map((header, index) => (
                      <TableCell sx={{ width: '200px' }} key={index}>{header}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {previewData.rows.map((row, rowIndex) => (
                    <TableRow key={rowIndex}>
                      {previewData.headers.map((header, cellIndex) => (
                        <TableCell sx={{ width: '200px' }} key={cellIndex}>{row[header]}</TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}

        {file && (
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={loading || !listingName}
            >
              {loading ? <CircularProgress size={24} /> : 'Import to Google Sheet'}
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default ExcelImport; 