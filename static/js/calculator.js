document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('bpmForm');
    const resultaat = document.getElementById('resultaat');
    const kentekenSection = document.getElementById('kentekenSection');
    const handmatigSection = document.getElementById('handmatigSection');
    const kentekenInput = document.getElementById('kenteken');
    const catalogusInput = document.getElementById('cataloguswaarde');
    const brandstofSection = document.getElementById('brandstofSection');
    const brandstofInputs = document.querySelectorAll('input[name="brandstof"]');
    const berekeningDetails = document.getElementById('berekeningDetails');
    const themeToggle = document.getElementById('themeToggle');
    let loadingState = false; // Add loading state variable
    const setLoadingState = (state) => {
        loadingState = state;
        updateButtonState();
    }; // Function to update loading state
    const updateButtonState = () => {
        const submitButton = document.querySelector('button[type="submit"]');
        submitButton.disabled = loadingState;
        submitButton.textContent = loadingState ? 'Laden...' : 'Bereken BPM';
    };

    // Reset required attributes of brandstof selector
    // because the default setting on page load is "Automatisch via kenteken"
    // which does not need brandstof to be selected
    brandstofInputs.forEach(input => input.removeAttribute('required'));

    // Theme toggle initialization
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    themeToggle.checked = savedTheme === 'light';

    themeToggle.addEventListener('change', function () {
        const theme = this.checked ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
    });

    // Format numbers as currency
    const formatCurrency = (number) => {
        return new Intl.NumberFormat('nl-NL', {
            style: 'currency',
            currency: 'EUR'
        }).format(number);
    };

    // Handle input method toggle
    document.querySelectorAll('input[name="invoermethode"]').forEach(radio => {
        radio.addEventListener('change', function () {
            form.reset();
            resultaat.style.display = 'none';

            if (this.value === 'kenteken') {
                kentekenSection.classList.add('show');
                handmatigSection.classList.remove('show');
                brandstofSection.classList.remove('show');
                kentekenInput.setAttribute('required', '');
                catalogusInput.removeAttribute('required');
                brandstofInputs.forEach(input => input.removeAttribute('required'));
                this.checked = true;
            } else {
                kentekenSection.classList.remove('show');
                handmatigSection.classList.add('show');
                brandstofSection.classList.add('show');
                kentekenInput.removeAttribute('required');
                catalogusInput.setAttribute('required', '');
                brandstofInputs.forEach(input => input.setAttribute('required', ''));
                this.checked = true;
            }
        });
    });

    // Validate kenteken input
    kentekenInput.addEventListener('input', function () {
        this.value = this.value.toUpperCase();
    });

    // Form submission handler
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (!form.checkValidity()) {
            console.log('Form is not valid');
            const invalidFields = form.querySelectorAll(':invalid');
            invalidFields.forEach(field => {
                console.log(`Invalid field: ${field.name}, value: ${field.value}`);
            });
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }

        const invoermethode = document.querySelector('input[name="invoermethode"]:checked').value;
        let cataloguswaarde;
        let bruto_bpm = 0;

        if (invoermethode === 'kenteken') {
            try {
                setLoadingState(true); // Set loading state to true
                const response = await fetch('/lookup_kenteken', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        kenteken: kentekenInput.value
                    })
                });

                if (!response.ok) {
                    throw new Error('Kenteken niet gevonden');
                }

                const data = await response.json();
                cataloguswaarde = data.cataloguswaarde;
                bruto_bpm = data.bruto_bpm || 0;

                // Automatically select the fuel type
                const fuelType = data.brandstof_omschrijving.toLowerCase();
                document.getElementById(fuelType).checked = true;
                setLoadingState(false); // Set loading state to false
            } catch (error) {
                setLoadingState(false); // Set loading state to false
                console.error('Error:', error);
                alert('Er is een fout opgetreden bij het ophalen van de kenteken gegevens. Probeer het opnieuw of voer de cataloguswaarde handmatig in.');
                return;
            }
        } else {
            cataloguswaarde = parseFloat(catalogusInput.value);
        }

        const brandstofType = document.querySelector('input[name="brandstof"]:checked').value;
        const afschrijving = parseFloat(document.getElementById('afschrijving').value);

        try {
            setLoadingState(true); // Set loading state to true
            const response = await fetch('/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cataloguswaarde: cataloguswaarde,
                    brandstof: brandstofType,
                    afschrijving: afschrijving,
                    bruto_bpm: bruto_bpm
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const result = await response.json();
            setLoadingState(false); // Set loading state to false

            // Display results
            document.getElementById('nettoCataloguswaarde').textContent =
                formatCurrency(result.netto_cataloguswaarde);
            document.getElementById('verhoogdBedrag').textContent =
                formatCurrency(result.verhoogd_bedrag);
            document.getElementById('teBetalen').textContent =
                formatCurrency(result.te_betalen);
            document.getElementById('brutoBPM').textContent =
                formatCurrency(result.bruto_bpm);

            resultaat.style.display = 'block';
            berekeningDetails.style.display = 'block';
        } catch (error) {
            setLoadingState(false); // Set loading state to false
            console.error('Error:', error);
            alert('Er is een fout opgetreden bij het berekenen van de BPM. Probeer het opnieuw.');
        }
    });
    // Add reset button functionality
    document.querySelector('button[type="reset"]').addEventListener('click', function (e) {
        e.preventDefault();
        form.reset();
        resultaat.style.display = 'none';
        // Reset to default view (kenteken)
        document.getElementById('kentekenMethode').checked = true;
        kentekenSection.classList.add('show');
        handmatigSection.classList.remove('show');
        brandstofSection.classList.remove('show');
        kentekenInput.setAttribute('required', '');
        catalogusInput.removeAttribute('required');
        brandstofInputs.forEach(input => input.removeAttribute('required'));
    });
});