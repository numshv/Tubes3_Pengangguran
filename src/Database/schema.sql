DROP DATABASE IF EXISTS pengangguran2;
CREATE DATABASE IF NOT EXISTS pengangguran2;
USE pengangguran2;

SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci';

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS ApplicationDetail;
DROP TABLE IF EXISTS ApplicantProfile;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE ApplicantProfile (
    applicant_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    date_of_birth DATE,
    address VARCHAR(255),
    phone_number VARCHAR(20)
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ApplicationDetail (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    application_role VARCHAR(100),
    cv_path TEXT,
    FOREIGN KEY (applicant_id) REFERENCES ApplicantProfile(applicant_id)
)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number) VALUES
-- Mohammad Nugraha Eka Prawira
(1, 'Moh4mm4d', 'Nu9r4h4', '2003-06-14', 'Jl. Kenanga No. 12, Jakarta', '081234567891'),
(2, 'MOH4MM4D', 'NUGR4H4', '2004-03-22', 'Jl. Melati No. 45, Bandung', '082123456781'),
(3, 'M0hammad', 'Nugr4h4', '2003-11-05', 'Jl. Cemara No. 7, Surabaya', '081345678912'),
(4, 'Mohammad', 'NUGR4H4', '2004-01-17', 'Jl. Sakura No. 4, Semarang', '082134567892'),
(5, 'm0h4mm4d', 'nu9r4h4', '2003-09-12', 'Jl. Mawar No. 9, Yogyakarta', '081223456789'),
(6, 'MoH4mM4d', 'NugR4h4', '2003-12-30', 'Jl. Anggrek No. 18, Medan', '082143256789'),
(7, 'M0H4MM4D', 'NuGr4Ha', '2003-05-26', 'Jl. Duku No. 33, Makassar', '081298765432'),
(8, 'Mohammad', 'NUGRAHA', '2004-02-11', 'Jl. Apel No. 2, Palembang', '081345679123'),
(9, 'm0H4mmad', 'nug9ah4', '2004-04-19', 'Jl. Jambu No. 25, Malang', '082198765432'),
(10, 'M0h4mM4D', 'NUGRAHA', '2003-07-07', 'Jl. Pisang No. 66, Denpasar', '081399988877'),
-- Ariel Herfrison
(11, 'Ari3l', 'H3rfri50n', '2004-03-14', 'Jl. Jeruk No. 2, Bekasi', '081223498761'),
(12, 'AR13L', 'H3RFR1S0N', '2003-08-03', 'Jl. Sawo No. 11, Depok', '082154321789'),
(13, '4riel', 'Herfris0n', '2003-11-23', 'Jl. Mangga No. 55, Tangerang', '081276543219'),
(14, 'AR1EL', 'H3RFR1S0N', '2003-02-09', 'Jl. Rambutan No. 88, Bogor', '082199876543'),
(15, 'Ariel', 'Herfrison', '2003-12-10', 'Jl. Durian No. 6, Cirebon', '081277789912'),
(16, 'ar13l', 'h3rfr150n', '2004-06-18', 'Jl. Nangka No. 90, Padang', '082134556789'),
(17, '4R13L', 'HERFRI50N', '2004-01-27', 'Jl. Srikaya No. 14, Batam', '081287654321'),
(18, 'Ari3L', 'HerfR150n', '2003-10-06', 'Jl. Kedondong No. 70, Solo', '082198123456'),
(19, 'Arie1', 'HERFRISON', '2004-02-03', 'Jl. Jambu No. 20, Balikpapan', '081256789123'),
(20, 'ARI3L', 'h3rfri50n', '2004-04-28', 'Jl. Salak No. 31, Pontianak', '082123987654'),
-- Farhan Nafis Rayhan
(21, 'F4rh4n', 'N4f15', '2004-05-05', 'Jl. Kamboja No. 12, Serang', '081254789621'),
(22, 'FARH4N', 'N4F15', '2003-06-15', 'Jl. Wijaya Kusuma No. 4, Cimahi', '082145678912'),
(23, 'F4rH4n', 'Nafis', '2003-08-09', 'Jl. Lili No. 7, Madiun', '081267898712'),
(24, 'Farh4n', 'N4FIS', '2004-01-30', 'Jl. Anyelir No. 1, Kediri', '082134987621'),
(25, 'f4rhan', 'naf15', '2003-04-17', 'Jl. Teratai No. 5, Tasikmalaya', '081233221234'),
(26, 'F4RH4N', 'N4F15', '2003-10-25', 'Jl. Dahlia No. 44, Manado', '082198726154'),
(27, 'f4RH4N', 'NAFIS', '2004-03-03', 'Jl. Tanjung No. 13, Palu', '081267891234'),
(28, 'FARH4N', 'N4f15', '2003-07-07', 'Jl. Ketapang No. 23, Kendari', '082111122233'),
(29, 'f4rh4n', 'naf15', '2004-02-20', 'Jl. Cemara No. 89, Kupang', '081299887766'),
(30, 'FARH4N', 'NAFIS', '2003-09-28', 'Jl. Flamboyan No. 5, Banjarmasin', '082133344455'),
-- Haikal Assyauqi
(31, 'H41k4l', '455y4uq1', '2003-05-15', 'Jl. Alpukat No. 13, Surakarta', '081222334455'),
(32, 'HA1K4L', 'ASSY4UQ1', '2004-07-22', 'Jl. Sukun No. 19, Pekanbaru', '082122334456'),
(33, 'Haikal', 'Assy4uqi', '2003-12-03', 'Jl. Nanas No. 33, Tegal', '081267845129'),
(34, 'H41k4L', 'Assyauqi', '2003-09-14', 'Jl. Pepaya No. 77, Cianjur', '082198772112'),
(35, 'ha1k4l', '455yauqi', '2003-01-01', 'Jl. Sawo No. 21, Banjar', '081212121212'),
(36, 'H41K4L', '455YAUQ1', '2004-03-30', 'Jl. Srikaya No. 34, Pangkalpinang', '082187654321'),
(37, 'h41K4L', 'Assy4Uq1', '2003-11-11', 'Jl. Damar No. 90, Mojokerto', '081232345678'),
(38, 'Ha1KaL', 'Assy4UqI', '2003-06-28', 'Jl. Jati No. 6, Magelang', '082167849512'),
(39, 'Haikal', 'ASSYAUQI', '2004-01-09', 'Jl. Jengkol No. 99, Blitar', '081289123456'),
(40, 'HA1KAL', '455y4UQ1', '2003-02-18', 'Jl. Kapuk No. 4, Probolinggo', '082145612378'),
-- Raden Francisco Trianto
(41, 'R4d3n', 'Fr4nC15c0', '2003-07-07', 'Jl. Mawar No. 1, Tasikmalaya', '081293847561'),
(42, 'RAD3N', 'FRANC15CO', '2004-06-13', 'Jl. Kamboja No. 23, Pontianak', '082145637291'),
(43, 'R4den', 'Francisco', '2003-04-04', 'Jl. Cemara No. 88, Pekalongan', '081223489127'),
(44, 'R4d3N', 'Fr4nc15co', '2003-12-25', 'Jl. Jeruk No. 4, Sukabumi', '082144478512'),
(45, 'r4d3n', 'fr4nc1sco', '2004-01-31', 'Jl. Mangga No. 56, Metro', '081267891255'),
(46, 'RADEN', 'FRANCISCO', '2004-04-17', 'Jl. Anggrek No. 45, Bitung', '082198123785'),
(47, 'RaD3n', 'FrAnC1sco', '2003-11-19', 'Jl. Apel No. 13, Lhokseumawe', '081212343434'),
(48, 'RaDen', 'FrAnC1SCo', '2003-03-09', 'Jl. Pisang No. 7, Sibolga', '082199998877'),
(49, 'r4d3n', 'Francisco', '2004-02-23', 'Jl. Duku No. 70, Serang', '081288899900'),
(50, 'R4d3N', 'FRANCISCO', '2003-08-08', 'Jl. Cempaka No. 6, Tarakan', '082122456789'),
-- Aland Mulia Pratama 
(51, '4l4nd', 'MuL14', '2003-07-10', 'Jl. Lontar No. 13, Pematangsiantar', '081234559999'),
(52, 'AL4ND', 'MUL1A', '2003-10-21', 'Jl. Waru No. 8, Salatiga', '082134556677'),
(53, 'Al4nd', 'Muli4', '2004-06-12', 'Jl. Belimbing No. 90, Blora', '081233445566'),
(54, 'ALAND', 'MULIA', '2003-05-01', 'Jl. Petai No. 21, Kuningan', '082199112233'),
(55, '4l4nd', 'muli4', '2003-09-29', 'Jl. Pinang No. 99, Bangkalan', '081223334455'),
(56, 'AlaNd', 'MuL14', '2004-03-20', 'Jl. Pisang No. 4, Singkawang', '082122223456'),
(57, '4L4ND', 'MUL1A', '2004-01-14', 'Jl. Durian No. 15, Ternate', '081256789456'),
(58, 'AlaND', 'MULIA', '2003-12-07', 'Jl. Duku No. 5, Bima', '082134567812'),
(59, 'ALaNd', 'MuLiA', '2003-02-26', 'Jl. Tomat No. 3, Ambon', '081245677899'),
(60, 'Aland', 'MuL1A', '2003-11-11', 'Jl. Rambutan No. 67, Bau-Bau', '082165432198'),
-- Ahmad Rafi Maliki
(61, '4hm4d', 'R4f1', '2003-09-12', 'Jl. Ketapang No. 3, Tarakan', '081256712348'),
(62, 'AHMAD', 'RAFI', '2004-04-19', 'Jl. Pinus No. 21, Mataram', '082176543210'),
(63, 'AhM4d', 'R4fi', '2003-08-28', 'Jl. Rambutan No. 17, Kupang', '081278765432'),
(64, '4Hmad', 'RAFI', '2003-07-04', 'Jl. Flamboyan No. 34, Tual', '082134598721'),
(65, 'Ahm4d', 'r4f1', '2004-02-12', 'Jl. Meranti No. 18, Tidore', '081233498765'),
(66, '4HMaD', 'RAF1', '2003-05-15', 'Jl. Salak No. 6, Sorong', '082177712345'),
(67, '4hmad', 'Rafi', '2003-11-03', 'Jl. Teratai No. 9, Langsa', '081287654398'),
(68, 'AHm4d', 'RaF1', '2004-06-01', 'Jl. Melati No. 29, Palopo', '082134589743'),
(69, 'Ahmad', 'RAFI', '2003-10-10', 'Jl. Cemara No. 77, Lubuklinggau', '081298765411'),
(70, '4HMAD', 'r4f1', '2004-01-01', 'Jl. Apel No. 89, Subulussalam', '082134672298'),
-- Ikhwan Al Hakim
(71, '1khw4n', '4lH4k1m', '2003-06-06', 'Jl. Kenari No. 23, Pariaman', '081223456789'),
(72, 'IKHW4N', 'ALH4KIM', '2003-10-25', 'Jl. Delima No. 2, Tebing Tinggi', '082167891234'),
(73, 'IkHwan', 'AlHak1m', '2004-03-18', 'Jl. Mahoni No. 44, Binjai', '081212398765'),
(74, '1KHWAN', '4lH4KIM', '2003-09-20', 'Jl. Tanjung No. 15, Tanjungpinang', '082123456781'),
(75, 'Ikhw4n', 'ALH4KIM', '2004-02-15', 'Jl. Beringin No. 6, Jambi', '081278991234'),
(76, '1khwan', '4lh4k1m', '2003-01-12', 'Jl. Bayam No. 11, Pangkalpinang', '082154321987'),
(77, '1kHw4N', '4lHaKIM', '2003-07-23', 'Jl. Singkong No. 9, Prabumulih', '081245678912'),
(78, 'Ikhwan', 'ALHAKIM', '2004-04-09', 'Jl. Bengkuang No. 20, Sungai Penuh', '082198762341'),
(79, 'IKHWAN', 'Alh4k1M', '2003-03-27', 'Jl. Nangka No. 14, Solok', '081277788899'),
(80, '1KHw4N', '4LHAKIM', '2004-01-19', 'Jl. Mangga No. 60, Padang Panjang', '082166655544');

INSERT INTO ApplicationDetail (detail_id, applicant_id, application_role, cv_path) VALUES
(1, 20, 'Software Developer', 'data/INFORMATION-TECHNOLOGY/15118506.pdf'),
(2, 27, 'Financial Planner', 'data/FINANCE/12858898.pdf'),
(3, 74, NULL, 'data/CHEF/11121498.pdf'),
(4, 13, 'Aviation Mechanic', 'data/AVIATION/11169163.pdf'),
(5, 42, 'Sales Consultant', 'data/SALES/15273850.pdf'),
(6, 19, 'Reconciliation Officer', 'data/ACCOUNTANT/12065211.pdf'),
(7, 34, 'Content Creator', 'data/DIGITAL-MEDIA/15353911.pdf'),
(8, 36, NULL, 'data/CONSTRUCTION/12839152.pdf'),
(9, 2, 'Site Supervisor', 'data/CONSTRUCTION/10820510.pdf'),
(10, 73, 'Public Affairs Specialist', 'data/PUBLIC-RELATIONS/11624880.pdf'),
(11, 3, 'Software Developer', 'data/INFORMATION-TECHNOLOGY/10553553.pdf'),
(12, 33, 'Cost Accountant', 'data/FINANCE/12071138.pdf'),
(13, 74, 'Anesthesiologist', 'data/HEALTHCARE/10466208.pdf'),
(14, 71, 'Process Associate', 'data/BPO/38707449.pdf'),
(15, 11, 'Lead Generation Specialist', 'data/BUSINESS-DEVELOPMENT/12814706.pdf'),
(16, 71, 'Illustrator', 'data/ARTS/16244633.pdf'),
(17, 55, NULL, 'data/ADVOCATE/12544735.pdf'),
(18, 59, 'Pilot', 'data/AVIATION/10189110.pdf'),
(19, 71, 'Soil Scientist', 'data/AGRICULTURE/17312146.pdf'),
(20, 6, 'Retail Banker', 'data/BANKING/11842348.pdf'),
(21, 49, 'Legal Researcher', 'data/ADVOCATE/13967854.pdf'),
(22, 60, NULL, 'data/TEACHER/15850434.pdf'),
(23, 74, 'Aircraft Maintenance Engineer', 'data/AVIATION/12043694.pdf'),
(24, 25, 'Bank Manager', 'data/BANKING/15553584.pdf'),
(25, 18, 'Intellectual Property Attorney', 'data/ADVOCATE/11773767.pdf'),
(26, 23, 'IT Consultant', 'data/CONSULTANT/12897903.pdf'),
(27, 24, 'Art Director', 'data/ARTS/11187796.pdf'),
(28, 62, 'Legal Advisor', 'data/ADVOCATE/11963737.pdf'),
(29, 47, 'Crisis Manager', 'data/PUBLIC-RELATIONS/11902276.pdf'),
(30, 38, 'Press Secretary', 'data/PUBLIC-RELATIONS/11850315.pdf');