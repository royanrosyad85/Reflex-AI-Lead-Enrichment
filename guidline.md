# Cara pengisian potensi polis dari data corporate customer

Dalam pengisian potensi polis saya di lihat dari kolom nama Perusahaan, sektor,
jumlah karyawan, jumlah cabang, Aset yang dimiliki Perusahaan Dan informasi dari kolom
lainnya. Data ini di gunakan untuk memetakan kebutuhan asuransi setiap corporate customer.
Basic penentuan nya di lihat dari sektor di tambah analisis infromasi dari kolom lainnya.
Penentuan potensi polis di sesuaikan dengan jenis product nya:

1. MV4: memiliki potensi jika Perusahaan memiliki armada mobil operasional banyak, tetapi
penggunaan armada yang tidak beresiko tinggi klaim
2. MV2: memiliki potensi jika Perusahaan memiliki banyak unit motor operasional
3. Personal Accident (PA) : Perusahan dengan banyak karyawan dan pekerjaan berat itu
memiliki potensi besar untuk employee Benefit. Sektor Industri seperti manufaktur
membutuhkan proteksi risiko kerja
4. Cargo Insurance: Perusahaan yang bergerak di sektor:
    · Logistic
    · perdagangan antar kota/antar pulau
    · Ekspor-impor
    · Distribusi barang
5. Heavy Equipment : Potensi untuk Perusahaan yang memakai
    · Excavator, loader, forklift,crane
    · Peralatan konstruksi dan lainnya
6. Marine: jika Perusahaan sektor logistic, kapal tambat/kapal industri, aktivitas operasi di
pelabuhan
7. Travel: jika Perusahaan melakukan perjalanan rutin karyawan.
8. Properti: Perusahaan memiliki Gedung kantor, pabrik, bangunan” lainnya
**Case:**
    ● Jadi jika Perusahaan Kontruksi : perkiraannya memiliki aset peralatan berat, banyak
       karyawan, resiko pekerjaan tinggi, dan mobil operasional maka potensi polisnya
       MV4,PA,HE
    ● Jika Perusahaan Manufaktur: : perkiraannya memiliki asset bangunan yang luas,
       banyak karyawan dan mobil operasional maka potensi polisnya MV4,PA,PROPERTI

