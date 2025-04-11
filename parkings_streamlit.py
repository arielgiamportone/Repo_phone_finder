import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from googlesearch import search
import time
import random

# Add fallback cities dictionary
CITIES = {
    "Madrid": "parking-madrid",
    "Barcelona": "parking-barcelona",
    "Valencia": "parking-valencia",
    "Sevilla": "parking-sevilla",
    "Málaga": "parking-malaga"
}

def get_available_cities():
    try:
        # Fetch the main page
        response = requests.get("https://parclick.es")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the cities menu
        cities_container = soup.find('div', class_='cities-menu')
        cities_dict = {}
        
        if cities_container:
            city_links = cities_container.find_all('a', href=True)
            for link in city_links:
                city_name = link.get_text(strip=True)
                # Extract the URL path and clean it
                city_url = link['href'].strip('/')
                if city_url.startswith('parking-'):
                    cities_dict[city_name] = city_url
        
        return cities_dict if cities_dict else CITIES  # Fallback to hardcoded cities if fetch fails
    except:
        return CITIES  # Fallback to hardcoded cities if any error occurs

def get_total_pages(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    pagination_nav = soup.find('nav', {'aria-label': 'Page navigation'})
    
    if not pagination_nav:
        return 1  # Si no hay paginación, asumimos 1 página
    
    # Extraer todos los números de página disponibles
    page_links = pagination_nav.find_all('a', href=True)
    pages = []
    for link in page_links:
        href = link['href']
        if '?page=' in href:
            try:
                page_num = int(href.split('?page=')[1].split('&')[0])
                pages.append(page_num)
            except (IndexError, ValueError):
                continue
    
    return max(pages) if pages else 1  # Máxima página encontrada

def get_parkings_from_page(url):
    time.sleep(1)  # Add delay to avoid rate limiting
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        parking_list = soup.find('ul', class_='grid grid-cols-2 lg:grid-cols-4 gap-4 text-grey-400 font-medium text-sm')
        
        parkings = []
        if parking_list:
            for li in parking_list.find_all('li'):
                link = li.find('a')
                if link:
                    parkings.append(link.get_text(strip=True))
        return parkings
    except Exception as e:
        st.warning(f"Error accessing page: {str(e)}")
        return []

def scrape_parkings(city_url, city_name):
    try:
        base_url = f"https://parclick.es/{city_url}"
        total_pages = get_total_pages(base_url)
        all_parkings = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page in range(1, total_pages + 1):
            page_url = f"{base_url}?page={page}"
            status_text.text(f"Extrayendo página {page}/{total_pages}")
            parkings = get_parkings_from_page(page_url)
            all_parkings.extend(parkings)
            progress_bar.progress(page/total_pages)
        
        unique_parkings = list(set(all_parkings))
        return unique_parkings
    except Exception as e:
        st.error(f"Error scraping parkings: {str(e)}")
        return []

def main():
    st.set_page_config(page_title="Parking Finder España", page_icon="🅿️")
    
    st.title("🅿️ Parking phone Finder - España")
    st.write("Encuentra los telefonos de los parkings disponibles en diferentes ciudades de España de parkclick.es")
    
    # Initialize session state for cities
    if 'available_cities' not in st.session_state:
        st.session_state.available_cities = get_available_cities()
    
    available_cities = st.session_state.available_cities
    
    # City selector with dynamic list
    selected_city = st.selectbox(
        "Selecciona una ciudad",
        sorted(available_cities.keys())
    )
    
    # Add option to disable phone search
    search_phones = st.checkbox("Buscar números de teléfono (puede tardar más)", value=True)
    
    if st.button("Buscar Parkings"):
        try:
            with st.spinner(f'Buscando parkings en {selected_city}...'):
                parkings = scrape_parkings(available_cities[selected_city], selected_city)
                
                if parkings:
                    st.success(f"✅ Se encontraron {len(parkings)} parkings en {selected_city}")
                    
                    # Create DataFrame
                    df = pd.DataFrame(columns=['Nombre del Parking', 'Teléfono'])
                    
                    if search_phones:
                        phone_progress = st.progress(0)
                        status = st.empty()
                        
                        for idx, parking in enumerate(sorted(parkings)):
                            status.text(f"Buscando teléfono para: {parking}")
                            phone = get_parking_phone(parking, selected_city)
                            df.loc[len(df)] = [parking, phone]
                            phone_progress.progress((idx + 1) / len(parkings))
                    else:
                        df = pd.DataFrame({
                            'Nombre del Parking': sorted(parkings),
                            'Teléfono': ['No buscado'] * len(parkings)
                        })
                    
                    # Display results
                    st.dataframe(df)
                    
                    # Download button
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Descargar CSV",
                        data=csv,
                        file_name=f'parkings_{selected_city.lower()}.csv',
                        mime='text/csv'
                    )
                else:
                    st.error("No se encontraron parkings en esta ciudad")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def get_parking_phone(parking_name, city):
    search_query = f"{parking_name} parking {city} teléfono contacto"
    try:
        # Add user agent and pause between requests
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents)
        }
        
        # Search in Google and take first 3 results
        for url in search(search_query, num_results=3, lang="es"):
            try:
                response = requests.get(url, timeout=5, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                text_content = soup.get_text()
                
                # Spanish phone patterns
                patterns = [
                    r'(?:[\+]?34)?[6789]\d{8}',  # Mobile and landline
                    r'(?:[\+]?34)?\s?[6789]\d{2}[\s-]?\d{2}[\s-]?\d{2}[\s-]?\d{2}'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text_content)
                    if matches:
                        # Clean the phone number
                        phone = re.sub(r'[\s-]', '', matches[0])
                        return phone
                
                time.sleep(random.uniform(2, 4))  # Random delay to avoid blocking
            except Exception as e:
                continue
    except Exception as e:
        st.warning(f"Error searching phone: {str(e)}")
    return "No encontrado"

if __name__ == "__main__":
    main()