import axios from 'axios'
import type {
  PersonalApplicationApi,
  VenueApiItem,
  VenueUsageRangeApi,
} from './types'

export async function fetchVenueUsageRange(startDate: string, endDate: string) {
  const { data } = await axios.get<VenueUsageRangeApi>('/api/v1/venues/usage-range', {
    params: { start_date: startDate, end_date: endDate },
  })
  return data
}

export async function fetchPersonalApplications() {
  const { data } = await axios.get<PersonalApplicationApi[]>('/api/v1/applications')
  return data
}

export async function fetchVenues() {
  const { data } = await axios.get<VenueApiItem[]>('/api/v1/venues')
  return data
}
