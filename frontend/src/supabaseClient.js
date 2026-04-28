import { createClient } from '@supabase/supabase-js'

// Replace these with YOUR actual Supabase URL and Key
const supabaseUrl = 'https://etqvwsasrtvjuaniwdxv.supabase.co'
const supabaseKey = 'sb_publishable_6AKOKhIrQwfgULYowu8CSA_3WBkb1Ul'

export const supabase = createClient(supabaseUrl, supabaseKey)