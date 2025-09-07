import React from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Box } from '@mui/material';

function BookingDataGrid({ bookings }) {
  const columns = [
    { field: 'guestName', headerName: 'Guest Name', width: 150 },
    { field: 'bookingCode', headerName: 'Booking Code', width: 150 },
    { field: 'checkInDate', headerName: 'Check-in Date', width: 150 },
    { field: 'checkOutDate', headerName: 'Check-out Date', width: 150 },
    { field: 'totalPrice', headerName: 'Total Price', width: 120 },
    { field: 'status', headerName: 'Status', width: 120, 
      renderCell: (params) => (
        <Box
          sx={{
            color: params.value === 'Canceled' ? 'red' : 'inherit',
            fontWeight: params.value === 'Canceled' ? 'bold' : 'normal',
          }}
        >
          {params.value}
        </Box>
      ),
    },
  ];

  return (
    <DataGrid
      rows={bookings}
      columns={columns}
      pageSize={5}
      rowsPerPageOptions={[5]}
      checkboxSelection
      disableRowSelectionOnClick
    />
  );
}

export default BookingDataGrid; 